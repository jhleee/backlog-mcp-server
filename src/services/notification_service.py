import asyncio
from typing import Optional, Dict, Any
import httpx
import logging
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.slack_webhook_url = settings.slack_webhook_url
        self.discord_webhook_url = None
        self._setup_discord_webhook()

    def _setup_discord_webhook(self):
        """Setup Discord webhook URL if bot token is provided"""
        if settings.discord_bot_token and settings.discord_channel_id:
            self.discord_webhook_url = f"discord://channel/{settings.discord_channel_id}"
            logger.info("Discord notifications configured")

    async def send_notification(self, message: str, channel: str = "general", priority: str = "normal") -> bool:
        """Send notification to configured channels"""
        success = False

        if self.slack_webhook_url:
            success = await self._send_slack_notification(message, channel, priority) or success

        if self.discord_webhook_url:
            success = await self._send_discord_notification(message, channel, priority) or success

        if not self.slack_webhook_url and not self.discord_webhook_url:
            logger.warning("No notification channels configured")

        return success

    async def _send_slack_notification(self, message: str, channel: str, priority: str) -> bool:
        """Send notification to Slack"""
        try:
            if not self.slack_webhook_url:
                return False

            payload = self._format_slack_message(message, channel, priority)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.slack_webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info(f"Slack notification sent to channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def _send_discord_notification(self, message: str, channel: str, priority: str) -> bool:
        """Send notification to Discord"""
        try:
            if not settings.discord_bot_token:
                return False

            import discord
            from discord.ext import commands

            intents = discord.Intents.default()
            intents.message_content = True

            bot = commands.Bot(command_prefix="!", intents=intents)

            @bot.event
            async def on_ready():
                try:
                    channel_obj = bot.get_channel(int(settings.discord_channel_id))
                    if channel_obj:
                        embed = self._format_discord_message(message, channel, priority)
                        await channel_obj.send(embed=embed)
                        logger.info(f"Discord notification sent to channel: {channel}")
                except Exception as e:
                    logger.error(f"Error sending Discord message: {e}")
                finally:
                    await bot.close()

            await bot.start(settings.discord_bot_token)
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def _format_slack_message(self, message: str, channel: str, priority: str) -> Dict[str, Any]:
        """Format message for Slack"""
        color = self._get_priority_color(priority)

        return {
            "username": "Git-Chat-Log",
            "icon_emoji": ":robot_face:",
            "attachments": [{
                "color": color,
                "title": f"{channel.replace('_', ' ').title()} Notification",
                "text": message,
                "footer": "Git-Chat-Log",
                "ts": int(datetime.now().timestamp())
            }]
        }

    def _format_discord_message(self, message: str, channel: str, priority: str):
        """Format message for Discord"""
        import discord

        color = self._get_discord_color(priority)

        embed = discord.Embed(
            title=f"{channel.replace('_', ' ').title()} Notification",
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Git-Chat-Log")

        return embed

    def _get_priority_color(self, priority: str) -> str:
        """Get color based on priority for Slack"""
        colors = {
            "high": "#ff0000",
            "normal": "#0099ff",
            "low": "#00ff00",
            "warning": "#ff9900",
            "info": "#0099ff"
        }
        return colors.get(priority, "#0099ff")

    def _get_discord_color(self, priority: str) -> int:
        """Get color based on priority for Discord"""
        colors = {
            "high": 0xff0000,
            "normal": 0x0099ff,
            "low": 0x00ff00,
            "warning": 0xff9900,
            "info": 0x0099ff
        }
        return colors.get(priority, 0x0099ff)

    async def send_meeting_reminder(self, meeting_title: str, participants: list, time_until: str):
        """Send meeting reminder"""
        message = f"📅 **Meeting Reminder**\n\n"
        message += f"**Title:** {meeting_title}\n"
        message += f"**Participants:** {', '.join(participants)}\n"
        message += f"**Time:** {time_until}\n"

        await self.send_notification(message, "meeting_reminders", "normal")

    async def send_task_assignment(self, task_title: str, assignee: str, due_date: Optional[str] = None):
        """Send task assignment notification"""
        message = f"📝 **New Task Assignment**\n\n"
        message += f"**Task:** {task_title}\n"
        message += f"**Assigned to:** {assignee}\n"

        if due_date:
            message += f"**Due Date:** {due_date}\n"

        await self.send_notification(message, "task_assignments", "normal")

    async def send_status_update(self, task_title: str, old_status: str, new_status: str, updated_by: str = "System"):
        """Send task status update notification"""
        message = f"🔄 **Task Status Update**\n\n"
        message += f"**Task:** {task_title}\n"
        message += f"**Status:** {old_status} → {new_status}\n"
        message += f"**Updated by:** {updated_by}\n"

        priority = "high" if new_status == "blocked" else "normal"
        await self.send_notification(message, "status_updates", priority)

    async def test_notification(self) -> Dict[str, bool]:
        """Test notification channels"""
        test_message = "🔔 This is a test notification from Git-Chat-Log"

        results = {
            "slack": False,
            "discord": False
        }

        if self.slack_webhook_url:
            results["slack"] = await self._send_slack_notification(
                test_message, "test", "info"
            )

        if settings.discord_bot_token:
            results["discord"] = await self._send_discord_notification(
                test_message, "test", "info"
            )

        return results