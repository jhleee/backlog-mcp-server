from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
import logging
import asyncio

from src.services.mcp_adapter import MCPAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["LangChain Agent"])

mcp_adapter = None


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ClearMemoryRequest(BaseModel):
    thread_id: Optional[str] = None


async def initialize_mcp_adapter():
    """Initialize the MCP adapter"""
    global mcp_adapter
    try:
        mcp_adapter = MCPAdapter()
        await mcp_adapter.load_mcp_tools()
        logger.info("MCP adapter initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP adapter: {e}")


@router.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Send a message to the LangChain agent"""
    if not mcp_adapter:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        response = await mcp_adapter.process_request(
            message=request.message,
            thread_id=request.thread_id
        )

        return {
            "success": True,
            "response": response,
            "thread_id": request.thread_id
        }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses"""
    await websocket.accept()

    if not mcp_adapter:
        await websocket.send_json({
            "error": "Agent not initialized"
        })
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            thread_id = data.get("thread_id", "default")

            if not message:
                await websocket.send_json({
                    "error": "Message is required"
                })
                continue

            for chunk in mcp_adapter.stream_response(message, thread_id):
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk
                })

            await websocket.send_json({
                "type": "complete",
                "thread_id": thread_id
            })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "error": str(e)
        })
    finally:
        await websocket.close()


@router.get("/history/{thread_id}")
async def get_history(thread_id: str) -> Dict[str, Any]:
    """Get conversation history for a specific thread"""
    if not mcp_adapter:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        history = mcp_adapter.get_conversation_history(thread_id)

        return {
            "success": True,
            "thread_id": thread_id,
            "history": history,
            "message_count": len(history)
        }

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/clear")
async def clear_memory(request: ClearMemoryRequest) -> Dict[str, Any]:
    """Clear conversation memory for a thread or all threads"""
    if not mcp_adapter:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        mcp_adapter.clear_memory(request.thread_id)

        return {
            "success": True,
            "message": f"Memory cleared for {'thread ' + request.thread_id if request.thread_id else 'all threads'}"
        }

    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def get_tools() -> Dict[str, Any]:
    """Get list of available tools"""
    if not mcp_adapter:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        tools = mcp_adapter.get_available_tools()

        return {
            "success": True,
            "tools": tools,
            "count": len(tools)
        }

    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agent_status() -> Dict[str, Any]:
    """Get agent status"""
    return {
        "success": True,
        "initialized": mcp_adapter is not None,
        "tools_loaded": len(mcp_adapter.get_available_tools()) if mcp_adapter else 0
    }