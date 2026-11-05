import asyncio
import json
import os
import signal
import subprocess
import time
import uuid
from pathlib import Path

from django.utils import timezone

from .runner_ipc import (
    RunnerIdentity,
    RunnerIdentityError,
    build_auth_response,
    get_container_boot_id,
    get_process_start_ticks,
    require_runner_secret,
    validate_live_process,
)


class RunnerSupervisorError(RuntimeError):
    pass


class BrowserRunnerSupervisor:
    def __init__(
        self,
        *,
        job_id,
        account_id,
        execution_generation,
        lock_owner_token,
        adapter_type,
        task_type,
        targets,
        options=None,
        existing_identity=None,
        existing_socket_path=None,
    ):
        self.job_id = str(job_id)
        self.account_id = int(account_id)
        self.execution_generation = int(execution_generation)
        self.lock_owner_token = lock_owner_token
        self.adapter_type = adapter_type
        self.task_type = task_type
        self.targets = list(targets)
        self.options = dict(options or {})
        self.runner_id = str(uuid.uuid4())
        self.profile_path = str(
            Path(os.getenv("INSTABOT_PROFILE_ROOT", "/app/profiles")) / str(account_id)
        )
        if existing_socket_path is not None:
            self.socket_path = Path(existing_socket_path)
            self.runner_id = str(existing_identity["runner_id"])
        else:
            self.socket_path = Path(
                "/tmp/instabot-runners"
            ) / f"{self.job_id}-{self.runner_id}.sock"
        self.identity = None
        if existing_identity is not None:
            self.identity = RunnerIdentity(
                runner_id=str(existing_identity["runner_id"]),
                pid=int(existing_identity["pid"]),
                start_ticks=int(existing_identity["start_ticks"]),
                container_boot_id=str(existing_identity["container_boot_id"]),
                pgid=int(existing_identity["pgid"]),
                execution_generation=self.execution_generation,
                job_id=self.job_id,
                profile_path=self.profile_path,
            )
        self.process = None
        self._reader = None
        self._writer = None
        self._connected = False

    def start(self):
        if not require_runner_secret():
            raise RunnerSupervisorError("Runner IPC secret is unavailable.")
        self.socket_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.socket_path.parent, 0o700)
        env = os.environ.copy()
        env.update(
            {
                "INSTABOT_RUNNER_ID": self.runner_id,
                "INSTABOT_RUNNER_JOB_ID": self.job_id,
                "INSTABOT_RUNNER_GENERATION": str(self.execution_generation),
                "INSTABOT_RUNNER_PROFILE_PATH": self.profile_path,
                "INSTABOT_RUNNER_SOCKET": str(self.socket_path),
            }
        )
        try:
            self.process = subprocess.Popen(
                [
                    "python",
                    "-m",
                    "orchestrator.runner_process",
                ],
                cwd="/app/backend",
                env=env,
                start_new_session=True,
            )
        except Exception as exc:
            raise RunnerSupervisorError("Could not start browser runner.") from exc

        pid = self.process.pid
        pgid = os.getpgid(pid)
        for _ in range(100):
            if self.socket_path.exists():
                break
            if self.process.poll() is not None:
                raise RunnerSupervisorError("Browser runner exited during startup.")
            time.sleep(0.05)
        if not self.socket_path.exists():
            raise RunnerSupervisorError("Browser runner IPC endpoint was not created.")
        try:
            self.identity = RunnerIdentity(
                runner_id=self.runner_id,
                pid=pid,
                start_ticks=get_process_start_ticks(pid),
                container_boot_id=get_container_boot_id(),
                pgid=pgid,
                execution_generation=self.execution_generation,
                job_id=self.job_id,
                profile_path=self.profile_path,
            )
        except RunnerIdentityError as exc:
            raise RunnerSupervisorError("Could not validate browser runner identity.") from exc
        if not validate_live_process(self.identity):
            raise RunnerSupervisorError("Browser runner identity validation failed.")
        return self.identity

    async def reconnect(self, timeout_seconds=10):
        if self.identity is None or not validate_live_process(self.identity):
            raise RunnerSupervisorError("Runner identity is stale or ambiguous.")
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if self.socket_path.exists():
                break
            await asyncio.sleep(0.05)
        if not self.socket_path.exists():
            raise RunnerSupervisorError("Runner IPC endpoint unavailable.")
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(self.socket_path)),
            timeout=max(0.1, deadline - asyncio.get_running_loop().time()),
        )
        line = await asyncio.wait_for(reader.readline(), timeout=2)
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RunnerSupervisorError("Runner IPC authentication challenge failed.")
        challenge = json.loads(line.decode("utf-8"))
        nonce = str(challenge["nonce"])
        expires_at = int(challenge["expires_at"])
        response = build_auth_response(
            secret=require_runner_secret(),
            identity=self.identity,
            nonce=nonce,
            expires_at=expires_at,
        )
        writer.write(
            json.dumps({"response": response}).encode("utf-8") + b"\n"
        )
        await writer.drain()
        accepted = await asyncio.wait_for(reader.readline(), timeout=2)
        if not accepted or json.loads(accepted)["ok"] is not True:
            writer.close()
            await writer.wait_closed()
            raise RunnerSupervisorError("Runner IPC authentication rejected.")
        self._reader = reader
        self._writer = writer
        self._connected = True
        return True

    async def request(self, command: str, payload=None):
        if not self._connected or self._writer is None:
            raise RunnerSupervisorError("Runner supervisor is not connected.")
        if not validate_live_process(self.identity):
            await self.disable_actions()
            raise RunnerSupervisorError("Runner process identity is no longer valid.")
        self._writer.write(
            json.dumps({"command": command, "payload": payload or {}}).encode("utf-8")
            + b"\n"
        )
        await self._writer.drain()
        line = await asyncio.wait_for(self._reader.readline(), timeout=30)
        if not line:
            raise RunnerSupervisorError("Runner disconnected.")
        response = json.loads(line.decode("utf-8"))
        if response.get("ok") is not True:
            raise RunnerSupervisorError(response.get("error", "Runner request rejected."))
        return response

    async def execute(self):
        payload = {
            "account_id": self.account_id,
            "job_id": self.job_id,
            "lock_owner_token": self.lock_owner_token,
            "execution_generation": self.execution_generation,
            "adapter_type": self.adapter_type,
            "task_type": self.task_type,
            "targets": self.targets,
            "options": self.options,
        }
        return await self.request("execute", payload)

    async def disable_actions(self):
        if self._connected:
            try:
                await asyncio.wait_for(self.request("disable_actions"), timeout=2)
            except Exception:
                pass

    async def close(self):
        await self.disable_actions()
        await self.shutdown_process_group()

    async def shutdown_process_group(self, grace_seconds=5):
        if self.identity is None:
            return False
        if not validate_live_process(self.identity):
            return True
        try:
            os.killpg(self.identity.pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            return True
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline:
            if not validate_live_process(self.identity):
                break
            await asyncio.sleep(0.05)
        if validate_live_process(self.identity):
            try:
                os.killpg(self.identity.pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        if self.process is not None:
            try:
                self.process.wait(timeout=max(0.2, grace_seconds))
            except subprocess.TimeoutExpired:
                pass
        if self.socket_path.exists():
            self.socket_path.unlink()
        return not validate_live_process(self.identity)
