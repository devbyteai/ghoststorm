"""Command execution sandbox for AI Assistant.

Provides safe command execution with:
- Whitelisted commands
- Blacklisted dangerous patterns
- Working directory restriction
- Timeout enforcement
- Output streaming
"""

from __future__ import annotations

import asyncio
import os
import re
import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncIterator

import structlog

logger = structlog.get_logger(__name__)


class CommandStatus(Enum):
    """Command execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


@dataclass
class CommandResult:
    """Result of command execution."""
    command: str
    status: CommandStatus
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: float
    blocked_reason: str | None = None


# Commands that are always allowed (read-only or safe)
WHITELISTED_COMMANDS = {
    # File system (read-only)
    "ls", "cat", "head", "tail", "less", "more", "file", "stat",
    "find", "locate", "which", "whereis", "wc", "du", "df",
    # Text processing
    "grep", "awk", "sed", "cut", "sort", "uniq", "diff", "tr",
    # Development tools
    "python", "python3", "pip", "pip3", "poetry", "uv",
    "node", "npm", "npx", "yarn", "pnpm",
    "git", "gh",
    # Build/test
    "pytest", "mypy", "ruff", "black", "isort", "flake8",
    "eslint", "prettier", "tsc",
    # Utilities
    "echo", "printf", "date", "env", "pwd", "basename", "dirname",
    "jq", "yq", "curl", "wget",
}

# Commands that require approval (can modify files)
APPROVAL_REQUIRED_COMMANDS = {
    "mkdir", "touch", "cp", "mv", "ln",
    "chmod", "chown",
    "git commit", "git push", "git merge", "git rebase",
    "pip install", "npm install", "poetry add",
}

# Patterns that are NEVER allowed
BLACKLISTED_PATTERNS = [
    # Destructive commands
    r"\brm\s+-rf\b",
    r"\brm\s+-r\b",
    r"\brm\s+--recursive\b",
    r"\brmdir\b",
    r"\bshred\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bformat\b",
    # Privilege escalation
    r"\bsudo\b",
    r"\bsu\b",
    r"\bdoas\b",
    r"\bpkexec\b",
    # Remote code execution
    r"curl\s+.*\|\s*(ba)?sh",
    r"wget\s+.*\|\s*(ba)?sh",
    r"\beval\b",
    r"\bexec\b",
    # System modification
    r"\bsystemctl\b",
    r"\bservice\b",
    r"\binit\b",
    r"\breboot\b",
    r"\bshutdown\b",
    r"\bhalt\b",
    r"\bpoweroff\b",
    # Network attacks
    r"\bnmap\b",
    r"\bnetcat\b",
    r"\bnc\s+-",
    r"\biptables\b",
    # Sensitive file access
    r"/etc/passwd",
    r"/etc/shadow",
    r"~/.ssh",
    r"\.env\b",
    r"credentials",
    r"secrets",
    # Fork bombs and resource exhaustion
    r":\(\)\{",
    r"\bfork\b",
    r"while\s+true",
    r"for\s*\(\s*;\s*;\s*\)",
]


class CommandSandbox:
    """Sandboxed command execution environment."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 1024 * 1024,  # 1MB
        allow_network: bool = True,
    ) -> None:
        """Initialize sandbox.

        Args:
            project_root: Root directory for command execution
            timeout_seconds: Maximum execution time
            max_output_bytes: Maximum output size
            allow_network: Whether to allow network access
        """
        self.project_root = Path(project_root).resolve()
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.allow_network = allow_network

        # Compile blacklist patterns
        self._blacklist_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in BLACKLISTED_PATTERNS
        ]

        logger.info(
            "Command sandbox initialized",
            project_root=str(self.project_root),
            timeout=timeout_seconds,
        )

    def validate_command(self, command: str) -> tuple[bool, str | None, bool]:
        """Validate a command before execution.

        Args:
            command: The command to validate

        Returns:
            Tuple of (is_allowed, blocked_reason, requires_approval)
        """
        # Check against blacklist first
        for pattern in self._blacklist_regex:
            if pattern.search(command):
                return False, f"Blocked pattern: {pattern.pattern}", False

        # Parse command to get base command
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command", False
            base_cmd = parts[0]
        except ValueError as e:
            return False, f"Invalid command syntax: {e}", False

        # Check if command tries to escape project root
        for part in parts:
            if ".." in part:
                # Resolve and check if it escapes
                try:
                    resolved = (self.project_root / part).resolve()
                    if not str(resolved).startswith(str(self.project_root)):
                        return False, "Path escapes project root", False
                except Exception:
                    pass

        # Check if base command is whitelisted
        if base_cmd in WHITELISTED_COMMANDS:
            # Check if this specific invocation requires approval
            for approval_cmd in APPROVAL_REQUIRED_COMMANDS:
                if command.startswith(approval_cmd):
                    return True, None, True
            return True, None, False

        # Check approval-required commands
        for approval_cmd in APPROVAL_REQUIRED_COMMANDS:
            if command.startswith(approval_cmd):
                return True, None, True

        # Unknown command - require approval
        return True, None, True

    async def execute(
        self,
        command: str,
        *,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """Execute a command in the sandbox.

        Args:
            command: Command to execute
            timeout: Override default timeout
            env: Additional environment variables

        Returns:
            CommandResult with execution details
        """
        import time
        start_time = time.monotonic()

        # Validate command
        is_allowed, blocked_reason, _ = self.validate_command(command)
        if not is_allowed:
            logger.warning(
                "Command blocked",
                command=command,
                reason=blocked_reason,
            )
            return CommandResult(
                command=command,
                status=CommandStatus.BLOCKED,
                stdout="",
                stderr=blocked_reason or "Command not allowed",
                exit_code=None,
                duration_ms=0,
                blocked_reason=blocked_reason,
            )

        # Build environment
        exec_env = os.environ.copy()
        exec_env["HOME"] = str(self.project_root)
        exec_env["PWD"] = str(self.project_root)
        if env:
            exec_env.update(env)

        # Execute command
        effective_timeout = timeout or self.timeout_seconds

        try:
            logger.debug("Executing command", command=command)

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
                env=exec_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration_ms = (time.monotonic() - start_time) * 1000

                logger.warning(
                    "Command timeout",
                    command=command,
                    timeout=effective_timeout,
                )

                return CommandResult(
                    command=command,
                    status=CommandStatus.TIMEOUT,
                    stdout="",
                    stderr=f"Command timed out after {effective_timeout}s",
                    exit_code=None,
                    duration_ms=duration_ms,
                )

            # Truncate output if too large
            stdout = stdout_bytes[:self.max_output_bytes].decode("utf-8", errors="replace")
            stderr = stderr_bytes[:self.max_output_bytes].decode("utf-8", errors="replace")

            duration_ms = (time.monotonic() - start_time) * 1000

            status = CommandStatus.COMPLETED if process.returncode == 0 else CommandStatus.FAILED

            logger.info(
                "Command completed",
                command=command,
                exit_code=process.returncode,
                duration_ms=duration_ms,
            )

            return CommandResult(
                command=command,
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Command execution error",
                command=command,
                error=str(e),
            )

            return CommandResult(
                command=command,
                status=CommandStatus.FAILED,
                stdout="",
                stderr=str(e),
                exit_code=None,
                duration_ms=duration_ms,
            )

    async def execute_stream(
        self,
        command: str,
        *,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        """Execute a command and stream output.

        Args:
            command: Command to execute
            timeout: Override default timeout
            env: Additional environment variables

        Yields:
            Output lines as they become available
        """
        # Validate command
        is_allowed, blocked_reason, _ = self.validate_command(command)
        if not is_allowed:
            yield f"[ERROR] Command blocked: {blocked_reason}\n"
            return

        # Build environment
        exec_env = os.environ.copy()
        exec_env["HOME"] = str(self.project_root)
        exec_env["PWD"] = str(self.project_root)
        if env:
            exec_env.update(env)

        effective_timeout = timeout or self.timeout_seconds

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.project_root),
                env=exec_env,
            )

            total_bytes = 0
            start_time = asyncio.get_event_loop().time()

            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > effective_timeout:
                    process.kill()
                    yield f"\n[TIMEOUT] Command exceeded {effective_timeout}s limit\n"
                    break

                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                if not line:
                    break

                total_bytes += len(line)
                if total_bytes > self.max_output_bytes:
                    yield "\n[TRUNCATED] Output exceeded size limit\n"
                    process.kill()
                    break

                yield line.decode("utf-8", errors="replace")

            await process.wait()

            if process.returncode != 0:
                yield f"\n[EXIT CODE: {process.returncode}]\n"

        except Exception as e:
            yield f"[ERROR] {e}\n"


class FileSandbox:
    """Sandboxed file access."""

    # Files that should never be read or written
    SENSITIVE_PATTERNS = [
        r"\.env$",
        r"\.env\.",
        r"credentials",
        r"secrets",
        r"\.pem$",
        r"\.key$",
        r"id_rsa",
        r"id_ed25519",
        r"\.ssh/",
        r"\.gnupg/",
        r"\.aws/",
        r"\.docker/config\.json",
    ]

    def __init__(self, project_root: str | Path) -> None:
        """Initialize file sandbox.

        Args:
            project_root: Root directory for file access
        """
        self.project_root = Path(project_root).resolve()
        self._sensitive_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SENSITIVE_PATTERNS
        ]

        logger.info(
            "File sandbox initialized",
            project_root=str(self.project_root),
        )

    def validate_path(self, path: str | Path) -> tuple[Path | None, str | None]:
        """Validate a file path.

        Args:
            path: Path to validate

        Returns:
            Tuple of (resolved_path, error_message)
        """
        try:
            # Resolve path relative to project root
            if Path(path).is_absolute():
                resolved = Path(path).resolve()
            else:
                resolved = (self.project_root / path).resolve()

            # Check if path is within project root
            if not str(resolved).startswith(str(self.project_root)):
                return None, "Path escapes project root"

            # Check against sensitive patterns
            path_str = str(resolved)
            for pattern in self._sensitive_regex:
                if pattern.search(path_str):
                    return None, "Access to sensitive file blocked"

            return resolved, None

        except Exception as e:
            return None, f"Invalid path: {e}"

    async def read_file(self, path: str | Path) -> tuple[str | None, str | None]:
        """Read a file safely.

        Args:
            path: Path to read

        Returns:
            Tuple of (content, error_message)
        """
        resolved, error = self.validate_path(path)
        if error:
            return None, error

        if not resolved.exists():
            return None, f"File not found: {path}"

        if not resolved.is_file():
            return None, f"Not a file: {path}"

        try:
            content = resolved.read_text(encoding="utf-8")
            logger.debug("File read", path=str(resolved))
            return content, None
        except Exception as e:
            return None, f"Error reading file: {e}"

    async def write_file(
        self,
        path: str | Path,
        content: str,
        *,
        create_dirs: bool = False,
    ) -> tuple[bool, str | None]:
        """Write a file safely.

        Args:
            path: Path to write
            content: Content to write
            create_dirs: Create parent directories if needed

        Returns:
            Tuple of (success, error_message)
        """
        resolved, error = self.validate_path(path)
        if error:
            return False, error

        try:
            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)

            resolved.write_text(content, encoding="utf-8")
            logger.info("File written", path=str(resolved))
            return True, None
        except Exception as e:
            return False, f"Error writing file: {e}"

    async def list_files(
        self,
        path: str | Path = ".",
        pattern: str = "*",
        recursive: bool = False,
    ) -> tuple[list[str] | None, str | None]:
        """List files in a directory.

        Args:
            path: Directory to list
            pattern: Glob pattern
            recursive: Include subdirectories

        Returns:
            Tuple of (file_list, error_message)
        """
        resolved, error = self.validate_path(path)
        if error:
            return None, error

        if not resolved.exists():
            return None, f"Directory not found: {path}"

        if not resolved.is_dir():
            return None, f"Not a directory: {path}"

        try:
            if recursive:
                files = list(resolved.rglob(pattern))
            else:
                files = list(resolved.glob(pattern))

            # Return relative paths
            relative_files = [
                str(f.relative_to(self.project_root))
                for f in files
                if f.is_file()
            ]

            return sorted(relative_files), None
        except Exception as e:
            return None, f"Error listing files: {e}"

    async def search_files(
        self,
        query: str,
        path: str | Path = ".",
        file_pattern: str = "*.py",
    ) -> tuple[list[dict] | None, str | None]:
        """Search for text in files.

        Args:
            query: Text to search for
            path: Directory to search
            file_pattern: Glob pattern for files

        Returns:
            Tuple of (matches, error_message)
        """
        resolved, error = self.validate_path(path)
        if error:
            return None, error

        if not resolved.exists():
            return None, f"Directory not found: {path}"

        try:
            matches = []
            pattern = re.compile(re.escape(query), re.IGNORECASE)

            for file_path in resolved.rglob(file_pattern):
                if not file_path.is_file():
                    continue

                # Skip sensitive files
                skip = False
                for sensitive in self._sensitive_regex:
                    if sensitive.search(str(file_path)):
                        skip = True
                        break
                if skip:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern.search(line):
                            matches.append({
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": i,
                                "content": line.strip()[:200],
                            })
                except Exception:
                    continue

            return matches[:100], None  # Limit results
        except Exception as e:
            return None, f"Error searching files: {e}"
