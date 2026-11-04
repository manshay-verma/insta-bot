OTP_TIMEOUT_SECONDS = 300


def otp_redis_key(job_id, execution_generation=None):
    if execution_generation is None:
        return f"automation:otp:{job_id}"
    return f"automation:otp:{job_id}:generation:{execution_generation}"
