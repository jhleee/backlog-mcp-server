from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class BacklogStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Backlog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique backlog ID")
    title: str = Field(..., description="Backlog item title")
    description: str = Field("", description="Detailed description")
    status: BacklogStatus = Field(BacklogStatus.TODO, description="Current status")
    assignee: Optional[str] = Field(None, description="Person assigned to this item")
    priority: int = Field(3, ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    due_date: Optional[datetime] = Field(None, description="Due date")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None)

    def to_markdown(self) -> str:
        """Convert backlog item to markdown format"""
        md_content = f"# {self.title}\n\n"
        md_content += f"**ID:** {self.id}\n"
        md_content += f"**Status:** {self.status.value}\n"
        md_content += f"**Priority:** {'⭐' * (6 - self.priority)}\n"

        if self.assignee:
            md_content += f"**Assignee:** {self.assignee}\n"

        if self.due_date:
            md_content += f"**Due Date:** {self.due_date.strftime('%Y-%m-%d')}\n"

        if self.tags:
            md_content += f"**Tags:** {', '.join(self.tags)}\n"

        md_content += "\n## Description\n"
        md_content += f"{self.description}\n\n"

        md_content += "## Metadata\n"
        md_content += f"- Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        md_content += f"- Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')}\n"

        if self.completed_at:
            md_content += f"- Completed: {self.completed_at.strftime('%Y-%m-%d %H:%M')}\n"

        return md_content

    @classmethod
    def from_markdown(cls, content: str, item_id: Optional[str] = None) -> "Backlog":
        """Parse backlog from markdown content"""
        lines = content.split('\n')

        title = ""
        backlog_id = item_id or str(uuid.uuid4())[:8]
        status = BacklogStatus.TODO
        assignee = None
        priority = 3
        tags = []
        due_date = None
        description = ""
        created_at = datetime.now()
        updated_at = datetime.now()
        completed_at = None

        current_section = None

        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
            elif line.startswith('**ID:**'):
                backlog_id = line.replace('**ID:**', '').strip()
            elif line.startswith('**Status:**'):
                status_str = line.replace('**Status:**', '').strip()
                try:
                    status = BacklogStatus(status_str)
                except:
                    status = BacklogStatus.TODO
            elif line.startswith('**Priority:**'):
                stars = line.count('⭐')
                priority = 6 - stars if stars > 0 else 3
            elif line.startswith('**Assignee:**'):
                assignee = line.replace('**Assignee:**', '').strip()
            elif line.startswith('**Due Date:**'):
                date_str = line.replace('**Due Date:**', '').strip()
                try:
                    due_date = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    due_date = None
            elif line.startswith('**Tags:**'):
                tags_str = line.replace('**Tags:**', '').strip()
                tags = [t.strip() for t in tags_str.split(',')]
            elif line.startswith('## Description'):
                current_section = 'description'
            elif line.startswith('## Metadata'):
                current_section = 'metadata'
            elif line.startswith('##'):
                current_section = None
            elif current_section == 'description':
                description += line + '\n'
            elif current_section == 'metadata':
                if 'Created:' in line:
                    date_str = line.split('Created:')[1].strip()
                    try:
                        created_at = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    except:
                        pass
                elif 'Updated:' in line:
                    date_str = line.split('Updated:')[1].strip()
                    try:
                        updated_at = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    except:
                        pass
                elif 'Completed:' in line:
                    date_str = line.split('Completed:')[1].strip()
                    try:
                        completed_at = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    except:
                        pass

        return cls(
            id=backlog_id,
            title=title,
            description=description.strip(),
            status=status,
            assignee=assignee,
            priority=priority,
            tags=tags,
            due_date=due_date,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at
        )

    def get_filename(self) -> str:
        """Generate filename for the backlog item"""
        return f"{self.id}.md"

    def is_overdue(self) -> bool:
        """Check if the backlog item is overdue"""
        if self.due_date and self.status not in [BacklogStatus.DONE, BacklogStatus.CANCELLED]:
            return datetime.now() > self.due_date
        return False

    def is_stale(self, days: int = 7) -> bool:
        """Check if the backlog item has not been updated for specified days"""
        if self.status not in [BacklogStatus.DONE, BacklogStatus.CANCELLED]:
            days_since_update = (datetime.now() - self.updated_at).days
            return days_since_update > days
        return False