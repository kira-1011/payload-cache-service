from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from cache_service.rate_limit import limiter
from cache_service.routers import payloads

app = FastAPI(title="Payload Cache Service")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # ty: ignore[invalid-argument-type]  # slowapi#188

app.include_router(payloads.router)
