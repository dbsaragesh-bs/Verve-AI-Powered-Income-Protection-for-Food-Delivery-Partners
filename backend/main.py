from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.database import close_db, init_db
from app.routes import (
    claims,
    dashboard,
    mobile,
    payouts,
    policies,
    premiums,
    simulation,
    workers,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await app.state.redis.ping()
    try:
        yield
    finally:
        redis_client: Redis = app.state.redis
        await redis_client.close()
        await close_db()


app = FastAPI(title="VERVE Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:19006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"
app.include_router(workers.router, prefix=api_prefix)
app.include_router(policies.router, prefix=api_prefix)
app.include_router(premiums.router, prefix=api_prefix)
app.include_router(claims.router, prefix=api_prefix)
app.include_router(payouts.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(mobile.router, prefix=api_prefix)
app.include_router(simulation.router, prefix=api_prefix)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
