import asyncio
import json
import os
import signal
import socket
import sys
import time
import uuid
from pathlib import Path

from .runner_ipc import (
    RunnerIdentityError,
    create_auth_challenge,
    require_runner_secret,
    validate_auth_response,
)


def _record_fake_browser(event: str, payload: dict) -> None:
    path = Path(os.environ.get("INSTABOT_FAKE_BROWSER_LOG", "/tmp/d16-fake-browser.jsonl"))
    record = {
        "event": event,
        "job_id": str(payload.get("job_id")),
        "execution_generation": int(payload.get("execution_generation")),
        "mode": "fake_browser",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


async def _execute_fake_browser(payload: dict) -> dict:
    """Deterministic stand-in for a browser operation. It never contacts Instagram."""
    _record_fake_browser("entered", payload)
    hold_path = os.environ.get("INSTABOT_FAKE_BROWSER_HOLD", "")
    if hold_path:
        command_path = Path(hold_path)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if not runner_process_state["browser_actions_enabled"]:
                raise RuntimeError("Fake browser lost supervisor ownership.")
            command = command_path.read_text(encoding="utf-8").strip() if command_path.exists() else "release"
            if command == "release":
                break
            await asyncio.sleep(0.05)
        else:
            raise TimeoutError("Fake browser hold expired.")
    _record_fake_browser("completed", payload)
    return {
        "success": True,
        "items_processed": 1,
        "errors": [],
        "data": {"mode": "fake_browser"},
    }


async def _execute_payload(payload: dict) -> dict:
    if os.environ.get("INSTABOT_FAKE_BROWSER") == "1":
        return await _execute_fake_browser(payload)

    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from orchestrator import AdapterType, TaskType, UnifiedWorker

    adapter_name = payload["adapter_type"]
    task_name = payload["task_type"]
    adapter_type = AdapterType(adapter_name)
    task_type = TaskType(task_name)
    worker = UnifiedWorker(
        account_id=int(payload["account_id"]),
        job_id=str(payload["job_id"]),
        lock_owner_token=str(payload["lock_owner_token"]),
        execution_generation=int(payload["execution_generation"]),
    )

    runner_process_state["worker"] = worker
    try:
        if not await worker.start_session():
            return {"success": False, "errors": ["Could not start backend automation session."]}

        options = dict(payload.get("options", {}))
        if adapter_type == AdapterType.PLAYWRIGHT:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()
            from api.tasks import _wait_for_job_otp

            async def verification_callback(_prompt):
                runner_process_state["awaiting_otp"] = True
                code = await _wait_for_job_otp(
                    payload["job_id"],
                    int(payload["execution_generation"]),
                )
                if not runner_process_state["browser_actions_enabled"]:
                    raise RuntimeError("OTP challenge lost supervisor ownership.")
                runner_process_state["awaiting_otp"] = False
                return code

            options["verification_callback"] = verification_callback
        result = await worker.execute(
            adapter_type,
            task_type,
            list(payload.get("targets", [])),
            **options,
        )
        return {
            "success": result.success,
            "items_processed": result.items_processed,
            "errors": list(result.errors or []),
            "data": result.data,
        }
    finally:
        await worker.cleanup()
        await worker.stop_session()


runner_process_state = {
    "worker": None,
    "browser_actions_enabled": True,
    "authenticated_connection": None,
    "seen_nonces": set(),
    "awaiting_otp": False,
}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    state = runner_process_state
    if state["authenticated_connection"] is not None:
        writer.close()
        await writer.wait_closed()
        return

    nonce, expires_at = create_auth_challenge()
    writer.write(json.dumps({"nonce": nonce, "expires_at": expires_at}).encode() + b"\n")
    await writer.drain()
    line = await reader.readline()
    if not line:
        writer.close()
        await writer.wait_closed()
        return
    try:
        auth = json.loads(line.decode("utf-8"))
        expected_secret = require_runner_secret()
        identity = runner_identity
        if not validate_auth_response(
            secret=expected_secret,
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
            response=str(auth.get("response", "")),
            seen_nonces=state["seen_nonces"],
        ):
            writer.close()
            await writer.wait_closed()
            return
    except (json.JSONDecodeError, RunnerIdentityError, TypeError, ValueError):
        writer.close()
        await writer.wait_closed()
        return

    state["authenticated_connection"] = writer
    state["browser_actions_enabled"] = True
    writer.write(b'{"ok":true}\n')
    await writer.drain()
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                request = json.loads(line.decode("utf-8"))
                command = request.get("command")
                if command == "identity":
                    response = {"ok": True, "identity": identity.as_dict()}
                elif command == "disable_actions":
                    state["browser_actions_enabled"] = False
                    response = {"ok": True}
                elif command == "execute" and state["browser_actions_enabled"]:
                    execute_task = asyncio.create_task(
                        _execute_payload(request["payload"])
                    )
                    disconnect_task = asyncio.create_task(reader.read(1))
                    done, pending = await asyncio.wait(
                        {execute_task, disconnect_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if disconnect_task in done:
                        disconnect_data = disconnect_task.result()
                        if not disconnect_data:
                            state["browser_actions_enabled"] = False
                            if state["awaiting_otp"]:
                                # Preserve the existing browser challenge. No browser
                                # action is allowed until a confirmed reconnect.
                                state["authenticated_connection"] = None
                                result = await execute_task
                                response = {"ok": True, "result": result}
                                break
                            execute_task.cancel()
                            await asyncio.gather(execute_task, return_exceptions=True)
                            response = {
                                "ok": False,
                                "error": "supervisor_connectivity_lost",
                            }
                            break
                        disconnect_task.cancel()
                        await asyncio.gather(disconnect_task, return_exceptions=True)
                    elif execute_task in done:
                        disconnect_task.cancel()
                        await asyncio.gather(disconnect_task, return_exceptions=True)
                    if not execute_task.done():
                        result = await execute_task
                    else:
                        result = execute_task.result()
                    if disconnect_task in done and disconnect_task.result():
                        disconnect_task = None
                    response = {"ok": True, "result": result}
                elif command == "shutdown":
                    response = {"ok": True}
                    writer.write(json.dumps(response).encode() + b"\n")
                    await writer.drain()
                    break
                else:
                    response = {"ok": False, "error": "browser_actions_disabled_or_unknown_command"}
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
            except Exception as exc:
                writer.write(
                    json.dumps({"ok": False, "error": type(exc).__name__}).encode() + b"\n"
                )
                await writer.drain()
    finally:
        state["browser_actions_enabled"] = False
        state["authenticated_connection"] = None
        if writer not in (None,):
            writer.close()
            await writer.wait_closed()


def main() -> None:
    global runner_identity
    runner_id = os.environ["INSTABOT_RUNNER_ID"]
    job_id = os.environ["INSTABOT_RUNNER_JOB_ID"]
    generation = int(os.environ["INSTABOT_RUNNER_GENERATION"])
    profile_path = os.environ["INSTABOT_RUNNER_PROFILE_PATH"]
    socket_path = Path(os.environ["INSTABOT_RUNNER_SOCKET"])
    socket_dir = socket_path.parent
    socket_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(socket_dir, 0o700)

    from .runner_ipc import (
        get_container_boot_id,
        get_process_start_ticks,
    )

    runner_identity = None
    pid = os.getpid()
    runner_identity = type("IdentityHolder", (), {})()
    from .runner_ipc import RunnerIdentity
    runner_identity = RunnerIdentity(
        runner_id=runner_id,
        pid=pid,
        start_ticks=get_process_start_ticks(pid),
        container_boot_id=get_container_boot_id(),
        pgid=os.getpgid(pid),
        execution_generation=generation,
        job_id=job_id,
        profile_path=profile_path,
    )

    if socket_path.exists():
        socket_path.unlink()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = loop.run_until_complete(
        asyncio.start_unix_server(handle_client, path=str(socket_path))
    )
    os.chmod(socket_path, 0o600)

    def stop(*_args):
        runner_process_state["browser_actions_enabled"] = False
        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        if socket_path.exists():
            socket_path.unlink()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == "__main__":
    main()
