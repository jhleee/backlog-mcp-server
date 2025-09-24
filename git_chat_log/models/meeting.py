from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import json


class Meeting(BaseModel):
    id: str = Field(..., description="Unique meeting ID")
    title: str = Field(..., description="Meeting title")
    date: datetime = Field(default_factory=datetime.now, description="Meeting date")
    participants: List[str] = Field(default_factory=list, description="List of participants")
    agenda: Optional[str] = Field(None, description="Meeting agenda")
    notes: Optional[str] = Field(None, description="Meeting notes")
    action_items: List[str] = Field(default_factory=list, description="Action items from the meeting")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Convert meeting to markdown format"""
        md_content = f"# {self.title}\n\n"
        md_content += f"**Date:** {self.date.strftime('%Y-%m-%d %H:%M')}\n"
        md_content += f"**Participants:** {', '.join(self.participants)}\n\n"

        if self.agenda:
            md_content += f"## Agenda\n{self.agenda}\n\n"

        if self.notes:
            md_content += f"## Notes\n{self.notes}\n\n"

        if self.action_items:
            md_content += "## Action Items\n"
            for item in self.action_items:
                md_content += f"- {item}\n"
            md_content += "\n"

        md_content += f"---\n"
        md_content += f"*Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}*\n"
        md_content += f"*Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')}*\n"

        return md_content

    @classmethod
    def from_markdown(cls, content: str, meeting_id: str) -> "Meeting":
        """Parse meeting from markdown content"""
        lines = content.split('\n')

        title = ""
        date = datetime.now()
        participants = []
        agenda = ""
        notes = ""
        action_items = []

        current_section = None

        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
            elif line.startswith('**Date:**'):
                date_str = line.replace('**Date:**', '').strip()
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                except:
                    date = datetime.now()
            elif line.startswith('**Participants:**'):
                participants_str = line.replace('**Participants:**', '').strip()
                participants = [p.strip() for p in participants_str.split(',')]
            elif line.startswith('## Agenda'):
                current_section = 'agenda'
            elif line.startswith('## Notes'):
                current_section = 'notes'
            elif line.startswith('## Action Items'):
                current_section = 'action_items'
            elif line.startswith('##'):
                current_section = None
            elif current_section == 'agenda':
                agenda += line + '\n'
            elif current_section == 'notes':
                notes += line + '\n'
            elif current_section == 'action_items' and line.startswith('- '):
                action_items.append(line[2:].strip())

        return cls(
            id=meeting_id,
            title=title,
            date=date,
            participants=participants,
            agenda=agenda.strip() if agenda else None,
            notes=notes.strip() if notes else None,
            action_items=action_items
        )

    def get_filename(self) -> str:
        """Generate filename for the meeting"""
        date_str = self.date.strftime('%Y-%m-%d')
        title_slug = self.title.lower().replace(' ', '-').replace('/', '-')[:50]
        return f"{date_str}-{title_slug}.md"