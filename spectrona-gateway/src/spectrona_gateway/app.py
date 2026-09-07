from fastapi import FastAPI

from .auth import auth_middleware
from .routes import health, openai_compat, anthropic_compat, events, integrations, local_compat, mcp, memory, policy, providers, ui


def create_app() -> FastAPI:
    app = FastAPI(
        title="Spectrona Gateway",
        version="0.1.0",
        description="Local-first AI gateway with DLP and audit logging",
    )
    app.middleware("http")(auth_middleware)
    app.include_router(health.router)
    app.include_router(openai_compat.router, prefix="/openai/v1")
    app.include_router(anthropic_compat.router, prefix="/anthropic/v1")
    app.include_router(local_compat.router, prefix="/local/v1")
    app.include_router(memory.router, prefix="/memory")
    app.include_router(events.router, prefix="/events")
    app.include_router(mcp.router, prefix="/mcp")
    app.include_router(integrations.router, prefix="/integrations")
    app.include_router(policy.router, prefix="/policy")
    app.include_router(providers.router, prefix="/providers")
    app.include_router(ui.router, prefix="/ui")
    return app


app = create_app()
