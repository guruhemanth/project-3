"""SubTrack FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .alerts.routes import router as alerts_router
from .auth.routes import router as auth_router
from .config import settings
from .database import ensure_all_tables, ping_db
from .rate_limit import auth_limiter, public_limiter
from .subscriptions.routes import router as subs_router

# Endpoints under this prefix get a tighter rate limit (see rate_limit_middleware).
_AUTH_PREFIX = "/api/auth/"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Self-heal on boot: confirm the DB is reachable and create any missing
    # tables so the server can start even if migrations never ran / a table
    # was dropped. Alembic is still the source of truth for schema evolution.
    if ping_db():
        created = ensure_all_tables()
        if created:
            print(f"[init] Database reachable. Created missing table(s): {created}")
        else:
            print("[init] Database reachable. All tables present.")
    else:
        print("[init][WARN] Database NOT reachable at startup; endpoints will "
              "error until it becomes available.")
    yield


app = FastAPI(title="SubTrack", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Health/docs/OpenAPI are exempt from limits for local dev ergonomics.
    path = request.url.path
    exempt = path in {"/health", "/docs", "/openapi.json", "/redoc"}
    # Auth endpoints (login/register/OTP) use a tighter bucket to blunt
    # credential brute-force and SMS-bombing.
    limiter = auth_limiter if path.startswith(_AUTH_PREFIX) else public_limiter
    if not exempt:
        client = request.client.host if request.client else "anon"
        allowed, remaining, limit, _ = limiter.check(client)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(limit),
                         "X-RateLimit-Remaining": "0"},
            )
    response: Response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limiter.limit)
    return response


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "subtrack"}


app.include_router(auth_router)
app.include_router(subs_router)
app.include_router(alerts_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
