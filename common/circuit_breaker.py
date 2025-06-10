import time


class CircuitBreaker:
    """
    Simple circuit breaker implementation per relay.

    States:
      - CLOSED: Allow requests normally.
      - OPEN: Reject requests until recovery timeout elapses.
      - HALF_OPEN: Allow a single request to test if the service has recovered.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = 'CLOSED'
        self.last_failure_time: float | None = None

    def allow_request(self) -> bool:
        if self.state == 'OPEN':
            elapsed = time.time() - (self.last_failure_time or 0)
            if elapsed >= self.recovery_timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = 'CLOSED'

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'