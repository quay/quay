def exponential_backoff(attempts, scaling_factor, base):
    backoff = 5 * (pow(2, attempts) - 1)
    backoff_time = backoff * scaling_factor
    retry_at = backoff_time / 10 + base
    return retry_at
