from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TextCron", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _register_routers():
    from app.api.translate import router as translate_router
    from app.api.validate import router as validate_router
    from app.api.feedback import router as feedback_router

    app.include_router(translate_router, prefix="/api")
    app.include_router(validate_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")


_register_routers()
