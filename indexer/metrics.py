"""
Shared Prometheus metrics for the indexer service.
Centralizes all metrics definitions to avoid registry collisions.
"""

from prometheus_client import Counter, Gauge

# Event processing metrics
EVENTS_RECEIVED = Counter(
    'events_received_total', 'Total number of events received from relays', ['relay_url']
)

EVENTS_QUEUED = Counter(
    'events_queued_total', 'Total number of events queued for processing'
)

EVENTS_PROCESSED = Counter(
    'events_processed_total', 'Total number of events successfully processed'
)

EVENTS_FAILED = Counter(
    'events_failed_total', 'Total number of events that failed processing'
)

EVENT_PROCESSING_ERRORS = Counter(
    'event_processing_errors_total', 'Total errors encountered during event processing'
)

EVENT_QUEUE_SIZE = Gauge(
    'event_queue_size', 'Current size of the event processing queue'
)

# Notification and error metrics
NOTIFICATION_ERRORS = Counter(
    'notification_errors_total', 'Total errors encountered in notification handling'
)

# Relay management metrics
RELAYS_CONFIGURED = Gauge(
    'relays_configured', 'Number of relays configured'
)

RELAYS_CONNECTED = Gauge(
    'relays_connected', 'Number of relays currently connected'
)

# Database metrics
DB_ACTIVE_CONNECTIONS = Gauge(
    'db_active_connections', 'Number of active database connections'
)

DB_IDLE_CONNECTIONS = Gauge(
    'db_idle_connections', 'Number of idle database connections'
)

DB_OPERATIONS = Counter(
    'db_operations_total', 'Total number of database operations', ['operation', 'status']
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half-open)', ['relay_url']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'circuit_breaker_failures_total', 'Total circuit breaker failures', ['relay_url']
)