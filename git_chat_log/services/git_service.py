import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import git
from git import Repo
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class GitService:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or settings.git_repo_path)
        self.repo: Optional[Repo] = None
        self._initialize_repo()

    def _initialize_repo(self) -> None:
        """Initialize or open Git repository"""
        self.repo_path.mkdir(parents=True, exist_ok=True)

        if not (self.repo_path / '.git').exists():
            logger.info(f"Initializing new Git repository at {self.repo_path}")
            self.repo = Repo.init(self.repo_path)
            self._configure_git()
            self._create_initial_structure()
        else:
            logger.info(f"Opening existing Git repository at {self.repo_path}")
            self.repo = Repo(self.repo_path)

    def _configure_git(self) -> None:
        """Configure Git user settings"""
        config = self.repo.config_writer()
        config.set_value("user", "name", settings.git_user_name)
        config.set_value("user", "email", settings.git_user_email)
        config.release()

    def _create_initial_structure(self) -> None:
        """Create initial directory structure"""
        directories = ['meetings', 'backlogs', 'archives']
        for dir_name in directories:
            dir_path = self.repo_path / dir_name
            dir_path.mkdir(exist_ok=True)
            (dir_path / '.gitkeep').touch()

        readme_content = """# Git-Chat-Log Repository

This repository contains meeting notes and backlog items managed by Git-Chat-Log.

## Structure
- `/meetings` - Meeting notes
- `/backlogs` - Backlog items
- `/archives` - Archived items
"""
        (self.repo_path / 'README.md').write_text(readme_content)

        self.repo.index.add(['*'])
        self.repo.index.commit("Initial repository structure")

    def create_file(self, path: str, content: str, commit_message: str) -> str:
        """Create a new file and commit it"""
        file_path = self.repo_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

        self.repo.index.add([path])
        commit = self.repo.index.commit(commit_message)

        logger.info(f"Created file {path} with commit {commit.hexsha}")
        return commit.hexsha

    def update_file(self, path: str, content: str, commit_message: str) -> str:
        """Update an existing file and commit changes"""
        file_path = self.repo_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"File {path} does not exist")

        file_path.write_text(content, encoding='utf-8')
        self.repo.index.add([path])
        commit = self.repo.index.commit(commit_message)

        logger.info(f"Updated file {path} with commit {commit.hexsha}")
        return commit.hexsha

    def read_file(self, path: str) -> str:
        """Read content from a file"""
        file_path = self.repo_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"File {path} does not exist")

        return file_path.read_text(encoding='utf-8')

    def delete_file(self, path: str, commit_message: str) -> str:
        """Delete a file and commit the deletion"""
        file_path = self.repo_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"File {path} does not exist")

        os.remove(file_path)
        self.repo.index.remove([path])
        commit = self.repo.index.commit(commit_message)

        logger.info(f"Deleted file {path} with commit {commit.hexsha}")
        return commit.hexsha

    def list_files(self, directory: str) -> List[str]:
        """List all files in a directory"""
        dir_path = self.repo_path / directory

        if not dir_path.exists():
            return []

        files = []
        for file_path in dir_path.glob('*.md'):
            if file_path.is_file():
                files.append(file_path.name)

        return sorted(files)

    def get_file_history(self, path: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a specific file"""
        history = []

        try:
            commits = list(self.repo.iter_commits(paths=path, max_count=limit))

            for commit in commits:
                history.append({
                    'sha': commit.hexsha,
                    'message': commit.message,
                    'author': commit.author.name,
                    'date': datetime.fromtimestamp(commit.committed_date),
                    'diff': commit.diff(commit.parents[0] if commit.parents else None, paths=path)
                })
        except Exception as e:
            logger.error(f"Error getting history for {path}: {e}")

        return history

    def search_files(self, pattern: str, directory: Optional[str] = None) -> List[str]:
        """Search for files matching a pattern"""
        search_path = self.repo_path / directory if directory else self.repo_path
        matching_files = []

        for file_path in search_path.rglob('*.md'):
            if file_path.is_file():
                content = file_path.read_text(encoding='utf-8')
                if pattern.lower() in content.lower():
                    matching_files.append(str(file_path.relative_to(self.repo_path)))

        return matching_files

    def archive_file(self, source_path: str, archive_reason: str) -> str:
        """Archive a file by moving it to the archives directory"""
        source_file = self.repo_path / source_path
        if not source_file.exists():
            raise FileNotFoundError(f"File {source_path} does not exist")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f"{timestamp}_{source_file.name}"
        archive_path = f"archives/{archive_name}"

        content = source_file.read_text(encoding='utf-8')
        archive_content = f"<!-- Archived: {archive_reason} -->\n{content}"

        (self.repo_path / 'archives').mkdir(exist_ok=True)
        (self.repo_path / archive_path).write_text(archive_content, encoding='utf-8')

        os.remove(source_file)
        self.repo.index.remove([source_path])
        self.repo.index.add([archive_path])

        commit = self.repo.index.commit(f"Archive {source_path}: {archive_reason}")

        logger.info(f"Archived {source_path} to {archive_path}")
        return commit.hexsha

    def push_to_remote(self, remote_name: str = 'origin', branch: str = 'main') -> bool:
        """Push changes to remote repository"""
        try:
            if not self.repo.remotes:
                logger.warning("No remote repository configured")
                return False

            remote = self.repo.remote(remote_name)
            remote.push(branch)
            logger.info(f"Pushed to {remote_name}/{branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to push to remote: {e}")
            return False

    def pull_from_remote(self, remote_name: str = 'origin', branch: str = 'main') -> bool:
        """Pull changes from remote repository"""
        try:
            if not self.repo.remotes:
                logger.warning("No remote repository configured")
                return False

            remote = self.repo.remote(remote_name)
            remote.pull(branch)
            logger.info(f"Pulled from {remote_name}/{branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull from remote: {e}")
            return False