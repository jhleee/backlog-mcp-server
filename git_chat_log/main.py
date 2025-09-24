from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os
import logging

from src.api import mcp_tools, agent_endpoints, mcp_server
from src.services import SchedulerService

load_dotenv()

scheduler = SchedulerService()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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
    docs_url="/docs"

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug
    )