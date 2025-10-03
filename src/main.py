from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os
import sys
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import mcp_tools, agent_endpoints, mcp_server
from src.services import SchedulerService
from config.settings import settings

load_dotenv()

security = HTTPBearer(auto_error=False)

scheduler = SchedulerService()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def verify_api_key(credentials: HTTPAuthorizationCredentials = None) -> bool:
    """Verify API key for authentication"""
    if not settings.api_key:
        # If no API key is configured, allow access (backward compatibility)
        return True

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    scheduler.start()
    # Initialize MCP adapter
    from src.api.agent_endpoints import initialize_mcp_adapter
    await initialize_mcp_adapter()
    logger.info("Application started")
    yield
    # Shutdown
    scheduler.stop()
    logger.info("Application shutdown")


app = FastAPI(
    title="Git-Chat-Log MCP Server",
    description="MCP server for Git-based meeting notes and backlog management with LangChain integration",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development() else None  # Disable docs in production

)

# CORS Configuration
cors_origins = settings.get_cors_origins() if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key Authentication Middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Middleware to verify API key for protected endpoints"""
    # Skip authentication for health check and root endpoints
    if request.url.path in ["/", "/health"]:
        return await call_next(request)

    # Verify API key if configured
    if settings.api_key:
        credentials = await security(request)
        await verify_api_key(credentials)

    response = await call_next(request)
    return response

# MCP Server endpoints (primary)
app.include_router(mcp_server.router, prefix="/mcp")

# Legacy endpoints
app.include_router(mcp_tools.router)
app.include_router(agent_endpoints.router)

@app.get("/")
async def root():
    return {
        "name": "Git-Chat-Log MCP Server",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # Use settings for configuration
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.is_development()  # Only reload in development
    )