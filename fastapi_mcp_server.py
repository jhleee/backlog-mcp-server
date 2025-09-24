#!/usr/bin/env python
"""
Git-Chat-Log FastAPI-MCP Server
Clean implementation using fastapi-mcp library
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

import uvicorn
from fastapi import FastAPI, APIRouter, Query
from pydantic import BaseModel, Field
from fastapi_mcp import FastApiMCP

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import services
try:
    from src.models import Meeting, Backlog, BacklogStatus
    from src.services import GitService, VectorService
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
    from models import Meeting, Backlog, BacklogStatus
    from services import GitService, VectorService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
git_service = GitService()
vector_service = VectorService()

# -- Pydantic Models --
class MeetingIn(BaseModel):
    title: str = Field(..., description="Meeting title")
    participants: List[str] = Field(default_factory=list, description="List of participants")
    date: Optional[str] = Field(None, description="Meeting date (ISO format)")
    agenda: Optional[str] = Field(None, description="Meeting agenda")
    notes: Optional[str] = Field(None, description="Meeting notes")

class MeetingOut(BaseModel):
    id: str
    file_path: str
    commit: str
    message: str

class BacklogIn(BaseModel):
    title: str = Field(..., description="Backlog item title")
    description: str = Field("", description="Detailed description")
    assignee: Optional[str] = Field(None, description="Person assigned")
    priority: int = Field(3, ge=1, le=5, description="Priority (1-5)")
    tags: List[str] = Field(default_factory=list, description="Tags")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")

class BacklogOut(BaseModel):
    id: str
    priority: int
    status: str
    message: str

class BacklogStatusUpdate(BaseModel):
    item_id: str = Field(..., description="Backlog item ID")
    status: str = Field(..., description="New status",
                       pattern="^(todo|in_progress|review|done|blocked|cancelled)$")

class BacklogUpdate(BaseModel):
    item_id: str = Field(..., description="Backlog item ID")
    title: Optional[str] = Field(None, description="Updated title")
    description: Optional[str] = Field(None, description="Updated description")
    assignee: Optional[str] = Field(None, description="Updated assignee")
    priority: Optional[int] = Field(None, ge=1, le=5, description="Updated priority (1-5)")
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    due_date: Optional[str] = Field(None, description="Updated due date (ISO format)")
    status: Optional[str] = Field(None, description="Updated status",
                                 pattern="^(todo|in_progress|review|done|blocked|cancelled)$")

class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query")
    n_results: int = Field(5, ge=1, le=20, description="Number of results")

class AdvancedQueryParams(BaseModel):
    # Full-text search
    full_text: Optional[str] = Field(None, description="Full-text search in title and description")
    title_contains: Optional[str] = Field(None, description="Search in title only")
    description_contains: Optional[str] = Field(None, description="Search in description only")

    # Field filters
    status: Optional[List[str]] = Field(None, description="Filter by status (can be multiple)")
    assignee: Optional[List[str]] = Field(None, description="Filter by assignee (can be multiple)")
    priority_min: Optional[int] = Field(None, ge=1, le=5, description="Minimum priority")
    priority_max: Optional[int] = Field(None, ge=1, le=5, description="Maximum priority")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (any match)")
    tags_all: Optional[List[str]] = Field(None, description="Filter by tags (all must match)")

    # Date filters
    created_after: Optional[str] = Field(None, description="Created after this date (ISO format)")
    created_before: Optional[str] = Field(None, description="Created before this date (ISO format)")
    updated_after: Optional[str] = Field(None, description="Updated after this date (ISO format)")
    updated_before: Optional[str] = Field(None, description="Updated before this date (ISO format)")
    due_after: Optional[str] = Field(None, description="Due after this date (ISO format)")
    due_before: Optional[str] = Field(None, description="Due before this date (ISO format)")
    has_due_date: Optional[bool] = Field(None, description="Filter by presence of due date")

    # Sorting
    sort_by: Optional[str] = Field("updated_at", description="Sort field (created_at, updated_at, due_date, priority, title, status)")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    # Pagination
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Skip this many results")

    # Additional options
    include_archived: bool = Field(False, description="Include archived items")
    include_stats: bool = Field(False, description="Include statistics in response")

# -- FastAPI App --
app = FastAPI(
    title="Git-Chat-Log MCP API",
    description="Git-based meeting and backlog management with MCP support",
    version="1.0.0"
)

# -- Meeting Router --
meeting_router = APIRouter(prefix="/meetings", tags=["Meetings"])

@meeting_router.post("/create", response_model=MeetingOut, operation_id="create_meeting")
def create_meeting_note(meeting: MeetingIn):
    """Create a new meeting note and commit to Git"""
    try:
        meeting_date = datetime.now()
        if meeting.date:
            meeting_date = datetime.fromisoformat(meeting.date)

        meeting_obj = Meeting(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            title=meeting.title,
            participants=meeting.participants,
            date=meeting_date,
            agenda=meeting.agenda,
            notes=meeting.notes
        )

        file_path = f"meetings/{meeting_obj.get_filename()}"
        content = meeting_obj.to_markdown()

        commit_sha = git_service.create_file(
            path=file_path,
            content=content,
            commit_message=f"Add meeting: {meeting_obj.title}"
        )

        logger.info(f"Created meeting: {meeting_obj.title}")

        return MeetingOut(
            id=meeting_obj.id,
            file_path=file_path,
            commit=commit_sha[:8],
            message=f"Created meeting '{meeting_obj.title}'"
        )
    except Exception as e:
        logger.error(f"Error creating meeting: {e}")
        raise

@meeting_router.get("/list", operation_id="list_meetings")
def list_meetings():
    """List all meeting notes"""
    try:
        meeting_files = git_service.list_files("meetings")
        meetings = []

        for file_name in meeting_files:
            content = git_service.read_file(f"meetings/{file_name}")
            meeting_id = file_name.replace(".md", "")
            meeting = Meeting.from_markdown(content, meeting_id)
            meetings.append({
                "id": meeting.id,
                "title": meeting.title,
                "date": meeting.date.isoformat(),
                "participants": meeting.participants
            })

        return {
            "count": len(meetings),
            "meetings": meetings
        }
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise

# -- Backlog Router --
backlog_router = APIRouter(prefix="/backlogs", tags=["Backlogs"])

@backlog_router.post("/create", response_model=BacklogOut, operation_id="create_backlog")
def create_backlog_item(backlog: BacklogIn):
    """Create a new backlog item and commit to Git"""
    try:
        due_date = None
        if backlog.due_date:
            due_date = datetime.fromisoformat(backlog.due_date)

        backlog_obj = Backlog(
            title=backlog.title,
            description=backlog.description,
            assignee=backlog.assignee,
            priority=backlog.priority,
            tags=backlog.tags,
            due_date=due_date
        )

        file_path = f"backlogs/{backlog_obj.get_filename()}"
        content = backlog_obj.to_markdown()

        commit_sha = git_service.create_file(
            path=file_path,
            content=content,
            commit_message=f"Add backlog: {backlog_obj.title}"
        )

        # Add to vector database
        vector_service.add_document(
            document_id=backlog_obj.id,
            text=f"{backlog_obj.title}\n{backlog_obj.description}",
            metadata={
                "type": "backlog",
                "status": backlog_obj.status.value,
                "assignee": backlog_obj.assignee,
                "priority": backlog_obj.priority,
                "created_at": backlog_obj.created_at.isoformat()
            }
        )

        logger.info(f"Created backlog: {backlog_obj.title}")

        return BacklogOut(
            id=backlog_obj.id,
            priority=backlog_obj.priority,
            status=backlog_obj.status.value,
            message=f"Created backlog item '{backlog_obj.title}'"
        )
    except Exception as e:
        logger.error(f"Error creating backlog: {e}")
        raise

@backlog_router.put("/update", operation_id="update_backlog")
def update_backlog(update: BacklogUpdate):
    """Update a backlog item with any field changes"""
    try:
        file_path = f"backlogs/{update.item_id}.md"
        content = git_service.read_file(file_path)
        backlog = Backlog.from_markdown(content, update.item_id)

        # Track changes for commit message
        changes = []

        # Update fields if provided
        if update.title is not None:
            old_title = backlog.title
            backlog.title = update.title
            changes.append(f"title from '{old_title}' to '{update.title}'")

        if update.description is not None:
            backlog.description = update.description
            changes.append("description")

        if update.assignee is not None:
            old_assignee = backlog.assignee
            backlog.assignee = update.assignee
            changes.append(f"assignee from '{old_assignee}' to '{update.assignee}'")

        if update.priority is not None:
            old_priority = backlog.priority
            backlog.priority = update.priority
            changes.append(f"priority from {old_priority} to {update.priority}")

        if update.tags is not None:
            backlog.tags = update.tags
            changes.append("tags")

        if update.due_date is not None:
            backlog.due_date = datetime.fromisoformat(update.due_date)
            changes.append(f"due date to {update.due_date}")

        if update.status is not None:
            old_status = backlog.status.value
            backlog.status = BacklogStatus(update.status)
            changes.append(f"status from '{old_status}' to '{update.status}'")
            if update.status == "done":
                backlog.completed_at = datetime.now()

        # Always update the updated_at timestamp
        backlog.updated_at = datetime.now()

        # Generate commit message
        if changes:
            commit_message = f"Update {backlog.title}: {', '.join(changes)}"
        else:
            commit_message = f"Update {backlog.title}"

        # Save to Git
        updated_content = backlog.to_markdown()
        commit_sha = git_service.update_file(
            path=file_path,
            content=updated_content,
            commit_message=commit_message
        )

        # Update vector database
        vector_service.update_document(
            document_id=backlog.id,
            text=f"{backlog.title}\n{backlog.description}",
            metadata={
                "type": "backlog",
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "updated_at": backlog.updated_at.isoformat()
            }
        )

        logger.info(f"Updated backlog: {backlog.title} with changes: {', '.join(changes) if changes else 'metadata only'}")

        return {
            "id": backlog.id,
            "title": backlog.title,
            "status": backlog.status.value,
            "changes": changes,
            "commit": commit_sha[:8],
            "message": f"Successfully updated backlog '{backlog.title}'"
        }
    except FileNotFoundError:
        logger.error(f"Backlog {update.item_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error updating backlog: {e}")
        raise

@backlog_router.put("/status", operation_id="update_backlog_status")
def update_backlog_status(update: BacklogStatusUpdate):
    """Update only the status of a backlog item (simplified endpoint)"""
    try:
        file_path = f"backlogs/{update.item_id}.md"
        content = git_service.read_file(file_path)
        backlog = Backlog.from_markdown(content, update.item_id)

        old_status = backlog.status.value
        backlog.status = BacklogStatus(update.status)
        backlog.updated_at = datetime.now()

        if update.status == "done":
            backlog.completed_at = datetime.now()

        updated_content = backlog.to_markdown()
        commit_sha = git_service.update_file(
            path=file_path,
            content=updated_content,
            commit_message=f"Update status of {backlog.title} to {update.status}"
        )

        # Update vector database
        vector_service.update_document(
            document_id=backlog.id,
            text=f"{backlog.title}\n{backlog.description}",
            metadata={
                "type": "backlog",
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "updated_at": backlog.updated_at.isoformat()
            }
        )

        logger.info(f"Updated backlog status: {backlog.title} from {old_status} to {update.status}")

        return {
            "id": backlog.id,
            "title": backlog.title,
            "old_status": old_status,
            "new_status": update.status,
            "commit": commit_sha[:8]
        }
    except Exception as e:
        logger.error(f"Error updating backlog status: {e}")
        raise

@backlog_router.post("/query", operation_id="query_backlogs_advanced")
def query_backlogs_advanced(params: AdvancedQueryParams):
    """Advanced backlog query with multiple filters, sorting, and pagination"""
    try:
        # Get all backlog files
        backlog_files = git_service.list_files("backlogs")
        all_backlogs = []

        # Load all backlogs
        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)
            all_backlogs.append(backlog)

        # Apply filters
        filtered_backlogs = []

        for backlog in all_backlogs:
            # Full-text search
            if params.full_text:
                text = f"{backlog.title} {backlog.description}".lower()
                if params.full_text.lower() not in text:
                    continue

            # Title search
            if params.title_contains:
                if params.title_contains.lower() not in backlog.title.lower():
                    continue

            # Description search
            if params.description_contains:
                if params.description_contains.lower() not in backlog.description.lower():
                    continue

            # Status filter
            if params.status:
                if backlog.status.value not in params.status:
                    continue

            # Assignee filter
            if params.assignee:
                if not backlog.assignee or backlog.assignee not in params.assignee:
                    continue

            # Priority filter
            if params.priority_min and backlog.priority < params.priority_min:
                continue
            if params.priority_max and backlog.priority > params.priority_max:
                continue

            # Tags filter (any match)
            if params.tags:
                if not any(tag in backlog.tags for tag in params.tags):
                    continue

            # Tags filter (all must match)
            if params.tags_all:
                if not all(tag in backlog.tags for tag in params.tags_all):
                    continue

            # Date filters
            if params.created_after:
                if backlog.created_at < datetime.fromisoformat(params.created_after):
                    continue
            if params.created_before:
                if backlog.created_at > datetime.fromisoformat(params.created_before):
                    continue

            if params.updated_after:
                if backlog.updated_at < datetime.fromisoformat(params.updated_after):
                    continue
            if params.updated_before:
                if backlog.updated_at > datetime.fromisoformat(params.updated_before):
                    continue

            if params.due_after and backlog.due_date:
                if backlog.due_date < datetime.fromisoformat(params.due_after):
                    continue
            if params.due_before and backlog.due_date:
                if backlog.due_date > datetime.fromisoformat(params.due_before):
                    continue

            # Has due date filter
            if params.has_due_date is not None:
                if params.has_due_date and not backlog.due_date:
                    continue
                if not params.has_due_date and backlog.due_date:
                    continue

            filtered_backlogs.append(backlog)

        # Sorting
        sort_key = lambda x: x
        if params.sort_by == "created_at":
            sort_key = lambda x: x.created_at
        elif params.sort_by == "updated_at":
            sort_key = lambda x: x.updated_at
        elif params.sort_by == "due_date":
            sort_key = lambda x: x.due_date or datetime.max
        elif params.sort_by == "priority":
            sort_key = lambda x: x.priority
        elif params.sort_by == "title":
            sort_key = lambda x: x.title.lower()
        elif params.sort_by == "status":
            sort_key = lambda x: x.status.value

        reverse = params.sort_order == "desc"
        filtered_backlogs.sort(key=sort_key, reverse=reverse)

        # Pagination
        total_count = len(filtered_backlogs)
        start_idx = params.offset
        end_idx = min(params.offset + params.limit, total_count)
        paginated_backlogs = filtered_backlogs[start_idx:end_idx]

        # Format results
        results = []
        for backlog in paginated_backlogs:
            results.append({
                "id": backlog.id,
                "title": backlog.title,
                "description": backlog.description,
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "tags": backlog.tags,
                "due_date": backlog.due_date.isoformat() if backlog.due_date else None,
                "created_at": backlog.created_at.isoformat(),
                "updated_at": backlog.updated_at.isoformat(),
                "completed_at": backlog.completed_at.isoformat() if backlog.completed_at else None,
                "is_overdue": backlog.is_overdue()
            })

        # Build response
        response = {
            "total": total_count,
            "count": len(results),
            "offset": params.offset,
            "limit": params.limit,
            "results": results
        }

        # Add statistics if requested
        if params.include_stats:
            stats = {
                "total_items": len(all_backlogs),
                "filtered_items": total_count,
                "by_status": {},
                "by_priority": {},
                "by_assignee": {},
                "overdue_count": 0,
                "with_due_date": 0
            }

            for backlog in filtered_backlogs:
                # Status stats
                status = backlog.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Priority stats
                priority = f"P{backlog.priority}"
                stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

                # Assignee stats
                if backlog.assignee:
                    stats["by_assignee"][backlog.assignee] = stats["by_assignee"].get(backlog.assignee, 0) + 1

                # Overdue and due date stats
                if backlog.is_overdue():
                    stats["overdue_count"] += 1
                if backlog.due_date:
                    stats["with_due_date"] += 1

            response["stats"] = stats

        return response

    except Exception as e:
        logger.error(f"Error in advanced query: {e}")
        raise

@backlog_router.get("/query", operation_id="query_backlogs_get")
def query_backlogs_get(
    # Full-text search
    full_text: Optional[str] = Query(None, description="Full-text search in title and description"),
    title_contains: Optional[str] = Query(None, description="Search in title only"),
    description_contains: Optional[str] = Query(None, description="Search in description only"),

    # Field filters
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by exact priority"),
    priority_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum priority"),
    priority_max: Optional[int] = Query(None, ge=1, le=5, description="Maximum priority"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (any match)"),

    # Date filters
    created_after: Optional[str] = Query(None, description="Created after this date"),
    updated_after: Optional[str] = Query(None, description="Updated after this date"),
    due_before: Optional[str] = Query(None, description="Due before this date"),
    has_due_date: Optional[bool] = Query(None, description="Filter by presence of due date"),

    # Sorting
    sort_by: Optional[str] = Query("updated_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),

    # Pagination
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),

    # Options
    include_stats: bool = Query(False, description="Include statistics")
):
    """Query backlogs with URL parameters (GET method)"""
    # Convert priority to priority_min and priority_max if exact priority is specified
    if priority is not None:
        priority_min = priority
        priority_max = priority

    # Create params object
    params = AdvancedQueryParams(
        full_text=full_text,
        title_contains=title_contains,
        description_contains=description_contains,
        status=status,
        assignee=[assignee] if assignee else None,
        priority_min=priority_min,
        priority_max=priority_max,
        tags=tags,
        created_after=created_after,
        updated_after=updated_after,
        due_before=due_before,
        has_due_date=has_due_date,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        include_stats=include_stats
    )

    # Use the same logic as POST endpoint
    return query_backlogs_advanced(params)

@backlog_router.post("/search", operation_id="search_backlogs")
def search_backlogs(search: SearchQuery):
    """Search for backlogs using natural language query"""
    try:
        results = vector_service.search(
            query=search.query,
            n_results=search.n_results,
            filter={"type": "backlog"}
        )

        return {
            "query": search.query,
            "count": results['count'],
            "results": results['results']
        }
    except Exception as e:
        logger.error(f"Error searching backlogs: {e}")
        raise

@backlog_router.get("/list", operation_id="list_backlogs")
def list_backlogs():
    """List all backlog items"""
    try:
        backlog_files = git_service.list_files("backlogs")
        backlogs = []

        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)
            backlogs.append({
                "id": backlog.id,
                "title": backlog.title,
                "status": backlog.status.value,
                "assignee": backlog.assignee,
                "priority": backlog.priority,
                "due_date": backlog.due_date.isoformat() if backlog.due_date else None
            })

        return {
            "count": len(backlogs),
            "backlogs": backlogs
        }
    except Exception as e:
        logger.error(f"Error listing backlogs: {e}")
        raise

@backlog_router.get("/overdue", operation_id="get_overdue_tasks")
def get_overdue_tasks():
    """Get all overdue backlog items"""
    try:
        backlog_files = git_service.list_files("backlogs")
        overdue_tasks = []

        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)

            if backlog.is_overdue():
                days_overdue = (datetime.now() - backlog.due_date).days if backlog.due_date else 0
                overdue_tasks.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "status": backlog.status.value,
                    "assignee": backlog.assignee,
                    "days_overdue": days_overdue,
                    "due_date": backlog.due_date.isoformat() if backlog.due_date else None
                })

        return {
            "count": len(overdue_tasks),
            "tasks": overdue_tasks
        }
    except Exception as e:
        logger.error(f"Error getting overdue tasks: {e}")
        raise

@backlog_router.get("/{item_id}", operation_id="get_backlog")
def get_backlog(item_id: str):
    """Get a specific backlog item by ID"""
    try:
        file_path = f"backlogs/{item_id}.md"
        content = git_service.read_file(file_path)
        backlog = Backlog.from_markdown(content, item_id)

        return {
            "id": backlog.id,
            "title": backlog.title,
            "description": backlog.description,
            "status": backlog.status.value,
            "assignee": backlog.assignee,
            "priority": backlog.priority,
            "tags": backlog.tags,
            "due_date": backlog.due_date.isoformat() if backlog.due_date else None,
            "created_at": backlog.created_at.isoformat(),
            "updated_at": backlog.updated_at.isoformat(),
            "completed_at": backlog.completed_at.isoformat() if backlog.completed_at else None
        }
    except FileNotFoundError:
        logger.error(f"Backlog {item_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error getting backlog: {e}")
        raise

@backlog_router.delete("/{item_id}", operation_id="delete_backlog")
def delete_backlog(item_id: str, archive: bool = True):
    """Delete a backlog item (optionally archive it first)"""
    try:
        file_path = f"backlogs/{item_id}.md"

        if archive:
            # Archive before deletion
            commit_sha = git_service.archive_file(file_path, "Archived before deletion")

            # Remove from vector database
            vector_service.delete_document(item_id)

            logger.info(f"Archived and deleted backlog {item_id}")

            return {
                "id": item_id,
                "status": "archived_and_deleted",
                "commit": commit_sha[:8],
                "message": f"Backlog {item_id} has been archived and deleted"
            }
        else:
            # Direct deletion without archiving
            commit_sha = git_service.delete_file(
                path=file_path,
                commit_message=f"Delete backlog {item_id}"
            )

            # Remove from vector database
            vector_service.delete_document(item_id)

            logger.info(f"Permanently deleted backlog {item_id}")

            return {
                "id": item_id,
                "status": "permanently_deleted",
                "commit": commit_sha[:8],
                "message": f"Backlog {item_id} has been permanently deleted"
            }
    except FileNotFoundError:
        logger.error(f"Backlog {item_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error deleting backlog: {e}")
        raise

@backlog_router.get("/stale/{days}", operation_id="get_stale_tasks")
def get_stale_tasks(days: int = 7):
    """Get backlog items not updated for specified days"""
    try:
        backlog_files = git_service.list_files("backlogs")
        stale_tasks = []

        for file_name in backlog_files:
            content = git_service.read_file(f"backlogs/{file_name}")
            backlog = Backlog.from_markdown(content)

            if backlog.is_stale(days):
                days_stale = (datetime.now() - backlog.updated_at).days
                stale_tasks.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "status": backlog.status.value,
                    "assignee": backlog.assignee,
                    "days_stale": days_stale,
                    "last_updated": backlog.updated_at.isoformat()
                })

        return {
            "count": len(stale_tasks),
            "days_threshold": days,
            "tasks": stale_tasks
        }
    except Exception as e:
        logger.error(f"Error getting stale tasks: {e}")
        raise

# -- Archive Router --
archive_router = APIRouter(prefix="/archives", tags=["Archives"])

@archive_router.post("/archive/{item_type}/{item_id}", operation_id="archive_item")
def archive_item(item_type: str, item_id: str, reason: str = "Manual archive"):
    """Archive a meeting or backlog item"""
    try:
        if item_type not in ["meeting", "backlog"]:
            raise ValueError("Item type must be 'meeting' or 'backlog'")

        source_dir = "meetings" if item_type == "meeting" else "backlogs"
        source_path = f"{source_dir}/{item_id}.md"

        commit_sha = git_service.archive_file(source_path, reason)

        logger.info(f"Archived {item_type} {item_id}: {reason}")

        return {
            "item_type": item_type,
            "item_id": item_id,
            "reason": reason,
            "commit": commit_sha[:8]
        }
    except Exception as e:
        logger.error(f"Error archiving item: {e}")
        raise

# -- Register routers with FastAPI app --
app.include_router(meeting_router)
app.include_router(backlog_router)
app.include_router(archive_router)

# -- Create and mount MCP server --
mcp = FastApiMCP(
    app,
    name="git-chat-log",
    description="Git-based meeting and backlog management MCP server"
)

# Mount the MCP server with SSE transport
mcp.mount_sse(mount_path="/mcp/sse")

# Mount the MCP server with HTTP transport (for testing)
mcp.mount_http(mount_path="/mcp")

# -- Root endpoint --
@app.get("/")
def root():
    return {
        "name": "Git-Chat-Log FastAPI-MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "redoc": "/redoc",
            "mcp_sse": "/mcp/sse",
            "mcp_http": "/mcp"
        },
        "services": [
            "meetings - Meeting management",
            "backlogs - Backlog management",
            "archives - Archive management"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "git": "operational",
            "vector_db": "operational"
        }
    }

# -- Main entry point --
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))

    logger.info(f"Starting FastAPI-MCP Server on {host}:{port}")
    logger.info(f"Documentation available at http://{host}:{port}/docs")

    uvicorn.run(
        "fastapi_mcp_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )