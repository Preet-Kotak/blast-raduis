"""FastAPI application entry point."""
from fastapi import FastAPI
from routes import users, items
from config import Settings

app = FastAPI(title="My API")
settings = Settings()

app.include_router(users.router, prefix="/users")
app.include_router(items.router, prefix="/items")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.environment}
