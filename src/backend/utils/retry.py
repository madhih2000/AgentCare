import logging
import random
import time
from functools import wraps

logger = logging.getLogger("agentcare.retry")


def retry(
    times: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    exceptions: tuple = (Exception,),
):
    """Retry a flaky call (e.g. an outbound LLM request) with exponential
    backoff + full jitter before giving up and letting the caller escalate/
    fail the workflow. Delay for attempt n is a random value in
    [0, min(max_delay, base_delay * 2**n)] — spreads out retries so a burst
    of 429s doesn't retry in lockstep."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, times + 2):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    logger.warning(
                        "Attempt %s/%s failed for %s: %s", attempt, times + 1, fn.__name__, exc
                    )
                    if attempt <= times:
                        delay = random.uniform(0, min(max_delay, base_delay * (2**attempt)))
                        time.sleep(delay)
            raise last_exc

        return wrapper

    return decorator
