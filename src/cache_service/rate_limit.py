from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Counters are kept in memory, per process.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
