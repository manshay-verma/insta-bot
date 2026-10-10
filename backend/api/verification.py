OTP_TIMEOUT_SECONDS = 300


def otp_redis_key(job_id):
    return f"automation:otp:{job_id}"
