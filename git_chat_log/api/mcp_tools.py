from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from src.models import Meeting, Backlog, BacklogStatus
from src.services import GitService, VectorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["MCP Tools"])

git_service = GitService()
vector_service = VectorService()


class CreateMeetingRequest(BaseModel):
    title: str
    participants: List[str]
    date: Optional[str] = None
    agenda: Optional[str] = None
    notes: Optional[str] = None


class CreateBacklogRequest(BaseModel):
    title: str
    description: str
    assignee: Optional[str] = None
    priority: int = 3
    tags: List[str] = []
    due_date: Optional[str] = None


class UpdateBacklogStatusRequest(BaseModel):
    item_id: str
    status: str


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


@router.post("/create_meeting_note")
async def create_meeting_note(request: CreateMeetingRequest) -> Dict[str, Any]:
    """Create a new meeting note and commit to Git"""
    try:
        meeting_date = datetime.now()
        if request.date:
            meeting_date = datetime.fromisoformat(request.date)

        meeting = Meeting(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            title=request.title,
            participants=request.participants,
            date=meeting_date,
            agenda=request.agenda,
            notes=request.notes
        )

        file_path = f"meetings/{meeting.get_filename()}"
        content = meeting.to_markdown()

        commit_sha = git_service.create_file(
            path=file_path,
            content=content,
            commit_message=f"Add meeting: {meeting.title}"
        )

        return {
            "success": True,
            "meeting_id": meeting.id,
            "file_path": file_path,
            "commit_sha": commit_sha
        }

    except Exception as e:
        logger.error(f"Failed to create meeting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create_backlog_item")
async def create_backlog_item(request: CreateBacklogRequest) -> Dict[str, Any]:
    """Create a new backlog item and commit to Git"""
    try:
        due_date = None
        if request.due_date:
            due_date = datetime.fromisoformat(request.due_date)

        backlog = Backlog(
            title=request.title,
            description=request.description,
            assignee=request.assignee,
            priority=request.priority,
            tags=request.tags,
            due_date=due_date
        )

        file_path = f"backlogs/{backlog.get_filename()}"
        content = backlog.to_markdown()

        commit_sha = git_service.create_file(
            path=file_path,
            content=content,
            commit_message=f"Add backlog: {backlog.title}"
        )

        vector_service.add_document(
            document_id=backlog.id,
            text=f"{backlog.title}\n{backlog.description}",
            metadata={
                "type": "backlog",
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "tags": backlog.tags,
                "created_at": backlog.created_at.isoformat()
            }
        )

        return {
            "success": True,
            "backlog_id": backlog.id,
            "file_path": file_path,
            "commit_sha": commit_sha
        }

    except Exception as e:
        logger.error(f"Failed to create backlog item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_backlog_status")
async def update_backlog_status(request: UpdateBacklogStatusRequest) -> Dict[str, Any]:
    """Update the status of a backlog item"""
    try:
        file_path = f"backlogs/{request.item_id}.md"
        content = git_service.read_file(file_path)

        backlog = Backlog.from_markdown(content, request.item_id)

        try:
            new_status = BacklogStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

        backlog.status = new_status
        backlog.updated_at = datetime.now()

        if new_status == BacklogStatus.DONE:
            backlog.completed_at = datetime.now()

        updated_content = backlog.to_markdown()
        commit_sha = git_service.update_file(
            path=file_path,
            content=updated_content,
            commit_message=f"Update status of {backlog.title} to {new_status.value}"
        )

        vector_service.update_document(
            document_id=backlog.id,
            text=f"{backlog.title}\n{backlog.description}",
            metadata={
                "type": "backlog",
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "tags": backlog.tags,
                "updated_at": backlog.updated_at.isoformat()
            }
        )

        return {
            "success": True,
            "backlog_id": backlog.id,
            "new_status": new_status.value,
            "commit_sha": commit_sha
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backlog item {request.item_id} not found")
    except Exception as e:
        logger.error(f"Failed to update backlog status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_backlogs_by_query")
async def search_backlogs_by_query(request: SearchRequest) -> Dict[str, Any]:
    """Search for backlogs using vector similarity search"""
    try:
        results = vector_service.search(
            query=request.query,
            n_results=request.n_results,
            filter={"type": "backlog"}
        )

        return {
            "success": True,
            "query": request.query,
            "results": results['results'],
            "count": results['count']
        }

    except Exception as e:
        logger.error(f"Failed to search backlogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_overdue_tasks")
async def get_overdue_tasks() -> Dict[str, Any]:
    """Get all overdue backlog items"""
    try:
        backlog_files = git_service.list_files("backlogs")
        overdue_tasks = []

        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)

            if backlog.is_overdue():
                overdue_tasks.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "assignee": backlog.assignee,
                    "due_date": backlog.due_date.isoformat() if backlog.due_date else None,
                    "status": backlog.status.value,
                    "days_overdue": (datetime.now() - backlog.due_date).days if backlog.due_date else 0
                })

        return {
            "success": True,
            "overdue_tasks": overdue_tasks,
            "count": len(overdue_tasks)
        }

    except Exception as e:
        logger.error(f"Failed to get overdue tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_stale_tasks")
async def get_stale_tasks(days: int = 7) -> Dict[str, Any]:
    """Get backlog items that haven't been updated for specified days"""
    try:
        backlog_files = git_service.list_files("backlogs")
        stale_tasks = []

        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)

            if backlog.is_stale(days):
                stale_tasks.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "assignee": backlog.assignee,
                    "status": backlog.status.value,
                    "last_updated": backlog.updated_at.isoformat(),
                    "days_stale": (datetime.now() - backlog.updated_at).days
                })

        return {
            "success": True,
            "stale_tasks": stale_tasks,
            "count": len(stale_tasks),
            "threshold_days": days
        }

    except Exception as e:
        logger.error(f"Failed to get stale tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize_text")
async def summarize_text(text: str, max_length: int = 200) -> Dict[str, Any]:
    """Summarize text (placeholder - requires LLM integration)"""
    try:
        summary = text[:max_length] + "..." if len(text) > max_length else text

        return {
            "success": True,
            "original_length": len(text),
            "summary": summary,
            "summary_length": len(summary)
        }

    except Exception as e:
        logger.error(f"Failed to summarize text: {e}")
        raise HTTPException(status_code=500, detail=str(e))