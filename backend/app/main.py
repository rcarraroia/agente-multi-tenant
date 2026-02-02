from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.db.supabase import get_supabase

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize resources
    try:
        # Check DB connection
        client = get_supabase()
        # Optional: Checking connection validity
    except Exception as e:
        print(f"Startup Error: {e}")
    
    yield
    
    # Shutdown: Clean up resources (Redis connections, etc)
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

# CORS Configuration
cors_origins = settings.cors_origins_list
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Default permissive CORS for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT, "version": "1.0.0"}

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
