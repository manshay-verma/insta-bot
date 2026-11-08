import hmac
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


RUNNER_SECRET_ENV = "INSTABOT_RUNNER_IPC_SECRET"
MAX_AUTH_AGE_SECONDS = 30


class RunnerIdentityError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunnerIdentity:
    runner_id: str
    pid: int
    start_ticks: int
    container_boot_id: str
    pgid: int
    execution_generation: int
    job_id: str
    profile_path: str

    def as_dict(self) -> dict:
        return asdict(self)


def get_container_boot_id() -> str:
    path = Path("/proc/sys/kernel/random/boot_id")
    if not path.exists():
        raise RunnerIdentityError("Linux boot identity is unavailable.")
    value = path.read_text(encoding="ascii").strip()
    if len(value) != 36:
        raise RunnerIdentityError("Linux boot identity is malformed.")
    return value


def parse_proc_stat(text: str):
    """Return (state, start_ticks) from /proc/<pid>/stat.

    The command field is wrapped in parentheses and may contain spaces, so the
    state is the token immediately after the final closing parenthesis.
    """
    if not isinstance(text, str):
        raise RunnerIdentityError("Runner process identity is malformed.")
    command_end = text.rfind(")")
    if command_end < 0 or command_end + 2 >= len(text):
        raise RunnerIdentityError("Runner process identity is malformed.")
    fields = text[command_end + 2 :].split()
    # state plus the following fields through starttime (proc(5) field 22).
    if len(fields) < 20 or len(fields[0]) != 1:
        raise RunnerIdentityError("Runner process identity is malformed.")
    try:
        start_ticks = int(fields[19])
    except ValueError as exc:
        raise RunnerIdentityError("Runner process identity is malformed.") from exc
    return fields[0], start_ticks


def _read_proc_stat(pid: int):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise RunnerIdentityError("Runner process identity is unavailable.")
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        text = stat_path.read_text(encoding="ascii")
    except FileNotFoundError as exc:
        raise RunnerIdentityError("Runner process identity is unavailable.") from exc
    return parse_proc_stat(text)


def get_process_start_ticks(pid: int) -> int:
    _state, start_ticks = _read_proc_stat(pid)
    return start_ticks


def validate_live_process(identity: RunnerIdentity) -> bool:
    if identity.pid <= 0 or identity.pgid <= 0:
        return False
    try:
        state, start_ticks = _read_proc_stat(identity.pid)
        if state in {"Z", "X"}:
            return False
        if start_ticks != identity.start_ticks:
            return False
        if os.getpgid(identity.pid) != identity.pgid:
            return False
        return get_container_boot_id() == identity.container_boot_id
    except (OSError, ValueError, RunnerIdentityError):
        return False


def require_runner_secret() -> bytes:
    secret = os.getenv(RUNNER_SECRET_ENV, "")
    if not secret:
        raise RunnerIdentityError(
            "INSTABOT_RUNNER_IPC_SECRET is required for process-level runner IPC."
        )
    return secret.encode("utf-8")


def canonical_identity(identity: RunnerIdentity) -> bytes:
    payload = {
        "runner_id": identity.runner_id,
        "pid": identity.pid,
        "start_ticks": identity.start_ticks,
        "container_boot_id": identity.container_boot_id,
        "pgid": identity.pgid,
        "execution_generation": identity.execution_generation,
        "job_id": identity.job_id,
        "profile_path": identity.profile_path,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def build_auth_response(
    *,
    secret: bytes,
    identity: RunnerIdentity,
    nonce: str,
    expires_at: int,
) -> str:
    message = (
        b"instabot-runner-auth-v1\x00"
        + nonce.encode("ascii")
        + b"\x00"
        + str(expires_at).encode("ascii")
        + b"\x00"
        + canonical_identity(identity)
    )
    import hashlib
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def validate_auth_response(
    *,
    secret: bytes,
    identity: RunnerIdentity,
    nonce: str,
    expires_at: int,
    response: str,
    seen_nonces: set,
) -> bool:
    now = int(time.time())
    if expires_at < now or expires_at - now > MAX_AUTH_AGE_SECONDS:
        return False
    if nonce in seen_nonces or len(nonce) < 32 or len(response) != 64:
        return False
    expected = build_auth_response(
        secret=secret,
        identity=identity,
        nonce=nonce,
        expires_at=expires_at,
    )
    if not hmac.compare_digest(expected, response):
        return False
    seen_nonces.add(nonce)
    return True


def create_auth_challenge() -> tuple[str, int]:
    return secrets.token_urlsafe(32), int(time.time()) + MAX_AUTH_AGE_SECONDS
