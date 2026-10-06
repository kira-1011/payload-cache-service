from fastapi import FastAPI

from cache_service.routers import payloads

app = FastAPI(title="Payload Cache Service")
app.include_router(payloads.router)
