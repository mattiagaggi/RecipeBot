from fastapi import FastAPI
from app.config.config import Settings
from app.config.logging_config import configure_logging
from app.api.chat import router as chat_router

# Configure logging as early as possible
configure_logging()

settings = Settings()
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

# Include the v1 router
app.include_router(chat_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
