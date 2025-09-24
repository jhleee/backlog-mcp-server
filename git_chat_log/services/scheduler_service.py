import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from config.settings import settings
from src.services.git_service import GitService
from src.services.notification_service import NotificationService
from src.models import Backlog

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.git_service = GitService()
        self.notification_service = NotificationService()
        self.jobs = {}

    def start(self):
        """Start the scheduler"""
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in settings")
            return

        self._setup_jobs()
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        self.add_job(
            job_id="check_overdue_tasks",
            func=self._check_overdue_tasks,
            trigger=CronTrigger(
                hour=settings.overdue_task_check_hour,
                minute=0
            ),
            name="Check for overdue tasks"
        )

        self.add_job(
            job_id="check_stale_tasks",
            func=self._check_stale_tasks,
            trigger=IntervalTrigger(
                hours=settings.scheduler_check_interval_hours
            ),
            name="Check for stale tasks"
        )

        self.add_job(
            job_id="daily_summary",
            func=self._send_daily_summary,
            trigger=CronTrigger(
                hour=9,
                minute=0
            ),
            name="Send daily summary"
        )

        logger.info(f"Setup {len(self.jobs)} scheduled jobs")

    def add_job(self, job_id: str, func, trigger, name: str = None, **kwargs):
        """Add a new job to the scheduler"""
        try:
            job = self.scheduler.add_job(
                func,
                trigger,
                id=job_id,
                name=name or job_id,
                **kwargs
            )
            self.jobs[job_id] = job
            logger.info(f"Added job: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
            return None

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler"""
        try:
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")

    def pause_job(self, job_id: str):
        """Pause a scheduled job"""
        try:
            if job_id in self.jobs:
                self.scheduler.pause_job(job_id)
                logger.info(f"Paused job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")

    def resume_job(self, job_id: str):
        """Resume a paused job"""
        try:
            if job_id in self.jobs:
                self.scheduler.resume_job(job_id)
                logger.info(f"Resumed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")

    async def _check_overdue_tasks(self):
        """Check for overdue backlog items and send notifications"""
        try:
            backlog_files = self.git_service.list_files("backlogs")
            overdue_tasks = []

            for file_name in backlog_files:
                content = self.git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                if backlog.is_overdue():
                    overdue_tasks.append({
                        "id": backlog.id,
                        "title": backlog.title,
                        "assignee": backlog.assignee,
                        "due_date": backlog.due_date.strftime("%Y-%m-%d") if backlog.due_date else None,
                        "days_overdue": (datetime.now() - backlog.due_date).days if backlog.due_date else 0
                    })

            if overdue_tasks:
                message = self._format_overdue_message(overdue_tasks)
                await self.notification_service.send_notification(
                    message=message,
                    channel="overdue_tasks"
                )
                logger.info(f"Found and notified about {len(overdue_tasks)} overdue tasks")

        except Exception as e:
            logger.error(f"Error checking overdue tasks: {e}")

    async def _check_stale_tasks(self):
        """Check for stale backlog items and send notifications"""
        try:
            backlog_files = self.git_service.list_files("backlogs")
            stale_tasks = []

            for file_name in backlog_files:
                content = self.git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                if backlog.is_stale(settings.stale_task_days):
                    stale_tasks.append({
                        "id": backlog.id,
                        "title": backlog.title,
                        "assignee": backlog.assignee,
                        "last_updated": backlog.updated_at.strftime("%Y-%m-%d"),
                        "days_stale": (datetime.now() - backlog.updated_at).days
                    })

            if stale_tasks:
                message = self._format_stale_message(stale_tasks)
                await self.notification_service.send_notification(
                    message=message,
                    channel="stale_tasks"
                )
                logger.info(f"Found and notified about {len(stale_tasks)} stale tasks")

        except Exception as e:
            logger.error(f"Error checking stale tasks: {e}")

    async def _send_daily_summary(self):
        """Send a daily summary of tasks"""
        try:
            backlog_files = self.git_service.list_files("backlogs")
            summary = {
                "total": len(backlog_files),
                "todo": 0,
                "in_progress": 0,
                "done": 0,
                "overdue": 0,
                "due_today": 0,
                "due_this_week": 0
            }

            today = datetime.now().date()
            week_end = today + timedelta(days=7)

            for file_name in backlog_files:
                content = self.git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                summary[backlog.status.value] = summary.get(backlog.status.value, 0) + 1

                if backlog.due_date:
                    due_date = backlog.due_date.date()
                    if due_date < today and backlog.status.value not in ["done", "cancelled"]:
                        summary["overdue"] += 1
                    elif due_date == today:
                        summary["due_today"] += 1
                    elif due_date <= week_end:
                        summary["due_this_week"] += 1

            message = self._format_daily_summary(summary)
            await self.notification_service.send_notification(
                message=message,
                channel="daily_summary"
            )
            logger.info("Sent daily summary")

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    def _format_overdue_message(self, tasks: List[Dict[str, Any]]) -> str:
        """Format overdue tasks message"""
        message = f"⚠️ **{len(tasks)} Overdue Tasks**\n\n"

        for task in tasks[:5]:
            message += f"• **{task['title']}**\n"
            if task['assignee']:
                message += f"  Assignee: {task['assignee']}\n"
            message += f"  Due: {task['due_date']} ({task['days_overdue']} days overdue)\n\n"

        if len(tasks) > 5:
            message += f"... and {len(tasks) - 5} more overdue tasks\n"

        return message

    def _format_stale_message(self, tasks: List[Dict[str, Any]]) -> str:
        """Format stale tasks message"""
        message = f"🕰️ **{len(tasks)} Stale Tasks**\n\n"
        message += f"Tasks not updated for more than {settings.stale_task_days} days:\n\n"

        for task in tasks[:5]:
            message += f"• **{task['title']}**\n"
            if task['assignee']:
                message += f"  Assignee: {task['assignee']}\n"
            message += f"  Last updated: {task['last_updated']} ({task['days_stale']} days ago)\n\n"

        if len(tasks) > 5:
            message += f"... and {len(tasks) - 5} more stale tasks\n"

        return message

    def _format_daily_summary(self, summary: Dict[str, Any]) -> str:
        """Format daily summary message"""
        message = "📊 **Daily Task Summary**\n\n"
        message += f"**Total Tasks:** {summary['total']}\n\n"
        message += "**Status Breakdown:**\n"
        message += f"• Todo: {summary.get('todo', 0)}\n"
        message += f"• In Progress: {summary.get('in_progress', 0)}\n"
        message += f"• Done: {summary.get('done', 0)}\n\n"

        if summary['overdue'] > 0:
            message += f"⚠️ **Overdue:** {summary['overdue']} tasks\n"

        if summary['due_today'] > 0:
            message += f"📅 **Due Today:** {summary['due_today']} tasks\n"

        if summary['due_this_week'] > 0:
            message += f"📆 **Due This Week:** {summary['due_this_week']} tasks\n"

        return message

    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get status of all jobs"""
        job_status = []
        for job_id, job in self.jobs.items():
            job_status.append({
                "id": job_id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "paused": job.next_run_time is None
            })
        return job_status