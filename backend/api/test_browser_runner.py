import asyncio
import os
import subprocess
import time
import sys
from pathlib import Path
from unittest import mock

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from account.models import BotAccount
from api.account_locks import (
    AccountLockBusy,
    AccountLockOwnershipError,
    acquire_account_lock,
    register_browser_runner,
    validate_browser_runner,
)
from api.models import AutomationJob
from orchestrator.runner_ipc import (
    RunnerIdentity,
    RunnerIdentityError,
    build_auth_response,
    create_auth_challenge,
    get_container_boot_id,
    get_process_start_ticks,
    parse_proc_stat,
    validate_auth_response,
    validate_live_process,
)


class RunnerIPCAuthenticationTests(SimpleTestCase):
    def _identity(self):
        pid = os.getpid()
        return RunnerIdentity(
            runner_id="11111111-1111-1111-1111-111111111111",
            pid=pid,
            start_ticks=get_process_start_ticks(pid),
            container_boot_id=get_container_boot_id(),
            pgid=os.getpgid(pid),
            execution_generation=4,
            job_id="22222222-2222-2222-2222-222222222222",
            profile_path="/tmp/profile",
        )

    def test_nonce_hmac_accepts_once_and_rejects_replay(self):
        secret = b"test-dedicated-runner-secret"
        identity = self._identity()
        nonce, expires_at = create_auth_challenge()
        response = build_auth_response(
            secret=secret,
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
        )
        seen = set()
        self.assertTrue(validate_auth_response(
            secret=secret,
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
            response=response,
            seen_nonces=seen,
        ))
        self.assertFalse(validate_auth_response(
            secret=secret,
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
            response=response,
            seen_nonces=seen,
        ))

    def test_wrong_secret_and_expired_nonce_fail_closed(self):
        identity = self._identity()
        nonce, expires_at = create_auth_challenge()
        response = build_auth_response(
            secret=b"correct-secret",
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
        )
        self.assertFalse(validate_auth_response(
            secret=b"wrong-secret",
            identity=identity,
            nonce=nonce,
            expires_at=expires_at,
            response=response,
            seen_nonces=set(),
        ))
        self.assertFalse(validate_auth_response(
            secret=b"correct-secret",
            identity=identity,
            nonce=nonce,
            expires_at=int(time.time()) - 1,
            response=response,
            seen_nonces=set(),
        ))

    def test_linux_process_identity_requires_all_process_fields(self):
        process = subprocess.Popen(
            ["python", "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        try:
            identity = RunnerIdentity(
                runner_id="11111111-1111-1111-1111-111111111111",
                pid=process.pid,
                start_ticks=get_process_start_ticks(process.pid),
                container_boot_id=get_container_boot_id(),
                pgid=os.getpgid(process.pid),
                execution_generation=1,
                job_id="22222222-2222-2222-2222-222222222222",
                profile_path="/tmp/profile",
            )
            self.assertTrue(validate_live_process(identity))
            stale = RunnerIdentity(**{
                **identity.as_dict(),
                "start_ticks": identity.start_ticks + 1,
            })
            self.assertFalse(validate_live_process(stale))
        finally:
            os.killpg(os.getpgid(process.pid), 9)
            process.wait(timeout=5)


class ProcessIdentityValidationTests(SimpleTestCase):
    def _identity_for_pid(self, pid):
        return RunnerIdentity(
            runner_id="11111111-1111-1111-1111-111111111111",
            pid=pid,
            start_ticks=get_process_start_ticks(pid),
            container_boot_id=get_container_boot_id(),
            pgid=os.getpgid(pid),
            execution_generation=1,
            job_id="22222222-2222-2222-2222-222222222222",
            profile_path="/tmp/profile",
        )

    def _stat_prefix(self, state):
        fields = " ".join(["1", "1", "1", "0", "-1", "0", "0", "0", "0", "0", "0", "0", "0", "0", "20", "0", "1", "0", "100"])
        return f"10 (test proc) {state} {fields}"

    def test_live_process_matches_identity(self):
        process = subprocess.Popen(["python", "-c", "import time; time.sleep(30)"], start_new_session=True)
        try:
            identity = self._identity_for_pid(process.pid)
            self.assertTrue(validate_live_process(identity))
        finally:
            os.killpg(os.getpgid(process.pid), 9)
            process.wait(timeout=5)

    def test_zombie_process_is_not_live(self):
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        try:
            deadline = time.monotonic() + 2
            state = ""
            while time.monotonic() < deadline:
                state, _ticks = parse_proc_stat(Path(f"/proc/{pid}/stat").read_text(encoding="ascii"))
                if state == "Z":
                    break
                time.sleep(0.01)
            self.assertEqual(state, "Z")
            identity = self._identity_for_pid(pid)
            self.assertFalse(validate_live_process(identity))
        finally:
            os.waitpid(pid, 0)

    def test_dead_and_missing_process_are_not_live(self):
        process = subprocess.Popen(["python", "-c", "import time; time.sleep(30)"], start_new_session=True)
        identity = self._identity_for_pid(process.pid)
        os.killpg(identity.pgid, 9)
        process.wait(timeout=5)
        self.assertFalse(validate_live_process(identity))
        missing = RunnerIdentity(**{**identity.as_dict(), "pid": 2**22, "pgid": 2**22})
        self.assertFalse(validate_live_process(missing))

    def test_start_tick_mismatch_rejects_pid_reuse(self):
        identity = self._identity_for_pid(os.getpid())
        reused = RunnerIdentity(**{**identity.as_dict(), "start_ticks": identity.start_ticks + 1})
        self.assertFalse(validate_live_process(reused))

    def test_malformed_or_unreadable_proc_is_not_live(self):
        identity = self._identity_for_pid(os.getpid())
        state, ticks = parse_proc_stat(self._stat_prefix("R"))
        self.assertEqual((state, ticks), ("R", 100))
        with self.assertRaises(RunnerIdentityError):
            parse_proc_stat("not a proc stat")
        with self.assertRaises(RunnerIdentityError):
            parse_proc_stat("1 (truncated)")
        with mock.patch("orchestrator.runner_ipc._read_proc_stat", return_value=("Z", identity.start_ticks)):
            self.assertFalse(validate_live_process(identity))
        with mock.patch("orchestrator.runner_ipc._read_proc_stat", return_value=("X", identity.start_ticks)):
            self.assertFalse(validate_live_process(identity))
        with mock.patch("orchestrator.runner_ipc._read_proc_stat", side_effect=PermissionError("denied")):
            self.assertFalse(validate_live_process(identity))
        with mock.patch("orchestrator.runner_ipc._read_proc_stat", side_effect=RunnerIdentityError("malformed")):
            self.assertFalse(validate_live_process(identity))


class BrowserRunnerLinuxIntegrationTests(SimpleTestCase):
    def test_runner_start_reconnect_and_process_group_shutdown(self):
        from orchestrator.runner_supervisor import (
            BrowserRunnerSupervisor,
            RunnerSupervisorError,
        )

        os.environ["INSTABOT_RUNNER_IPC_SECRET"] = "test-linux-integration-secret"
        supervisor = BrowserRunnerSupervisor(
            job_id="22222222-2222-2222-2222-222222222222",
            account_id=999,
            execution_generation=7,
            lock_owner_token="owner-token",
            adapter_type="playwright",
            task_type="scrape_profile",
            targets=["example"],
        )

        async def exercise():
            identity = supervisor.start()
            await supervisor.reconnect(timeout_seconds=5)
            identity_response = await supervisor.request("identity")
            self.assertEqual(
                identity_response["identity"]["runner_id"],
                identity.runner_id,
            )
            competing = BrowserRunnerSupervisor(
                job_id=supervisor.job_id,
                account_id=999,
                execution_generation=7,
                lock_owner_token="owner-token",
                adapter_type="playwright",
                task_type="scrape_profile",
                targets=["example"],
                existing_identity={
                    "runner_id": identity.runner_id,
                    "pid": identity.pid,
                    "start_ticks": identity.start_ticks,
                    "container_boot_id": identity.container_boot_id,
                    "pgid": identity.pgid,
                },
                existing_socket_path=str(supervisor.socket_path),
            )
            with self.assertRaises(RunnerSupervisorError):
                await competing.reconnect(timeout_seconds=1)
            await supervisor.close()

        asyncio.run(exercise())
        self.assertFalse(validate_live_process(supervisor.identity))


class BrowserRunnerDatabaseTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="runner-owner",
            password="test-password",
        )
        self.account = BotAccount.objects.create(
            owner=user,
            username="runner-account",
            password_encrypted="encrypted",
        )
        self.job = AutomationJob.objects.create(
            user=user,
            account=self.account,
            action="scrape_profile",
            targets=["example"],
            status=AutomationJob.Status.RUNNING,
        )
        self.job.execution_generation = 1
        self.job.save(update_fields=["execution_generation"])

    def _identity(self):
        process = subprocess.Popen(
            ["python", "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        return process, RunnerIdentity(
            runner_id="11111111-1111-1111-1111-111111111111",
            pid=process.pid,
            start_ticks=get_process_start_ticks(process.pid),
            container_boot_id=get_container_boot_id(),
            pgid=os.getpgid(process.pid),
            execution_generation=1,
            job_id=str(self.job.id),
            profile_path="/tmp/runner-profile",
        )

    def test_register_and_validate_confirmed_runner(self):
        process, identity = self._identity()
        try:
            lock = acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                execution_generation=1,
            )
            register_browser_runner(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=1,
                runner=identity,
                runner_ipc_path="/tmp/runner.sock",
            )
            confirmed = validate_browser_runner(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=1,
            )
            self.assertEqual(confirmed.runner_id, identity.runner_id)
        finally:
            os.killpg(os.getpgid(process.pid), 9)
            process.wait(timeout=5)

    def test_expired_lock_does_not_become_reusable_without_process_fencing(self):
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=1,
        )
        from django.utils import timezone
        from datetime import timedelta
        from api.models import AccountBrowserLock
        db_lock = AccountBrowserLock.objects.get(account_id=self.account.id)
        db_lock.expires_at = timezone.now() - timedelta(seconds=1)
        db_lock.save(update_fields=["expires_at"])
        with self.assertRaises(AccountLockBusy):
            acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=1,
            )
