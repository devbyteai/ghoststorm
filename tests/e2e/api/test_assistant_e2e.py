"""E2E tests for AI Assistant API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantChatAPI:
    """Tests for /api/assistant/chat endpoint."""

    def test_chat_success(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test successful chat message."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.chat = AsyncMock(return_value="Hello! How can I help you?")
            mock_agent.get_pending_approvals = MagicMock(return_value=[])
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "Hello", "stream": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data["has_pending_actions"] is False

    def test_chat_with_pending_actions(
        self,
        api_test_client: TestClient,
    ):
        """Test chat response indicates pending actions."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.chat = AsyncMock(return_value="I need to run a command...")
            mock_agent.get_pending_approvals = MagicMock(
                return_value=[{"id": "abc123", "type": "execute"}]
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "Run tests", "stream": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_pending_actions"] is True

    def test_chat_empty_message(self, api_test_client: TestClient):
        """Test chat with empty message."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={"message": "", "stream": False},
        )
        # Empty message may be allowed or rejected based on implementation
        assert response.status_code in [200, 422]


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantFilesAPI:
    """Tests for /api/assistant/files endpoints."""

    def test_list_files_success(self, api_test_client: TestClient):
        """Test listing files in a directory."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.list_files = AsyncMock(
                return_value=(["file1.py", "file2.py", "dir/"], None)
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get(
                "/api/assistant/files",
                params={"path": ".", "pattern": "*.py"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "files" in data
            assert data["error"] is None

    def test_list_files_recursive(self, api_test_client: TestClient):
        """Test listing files recursively."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.list_files = AsyncMock(
                return_value=(["src/main.py", "tests/test_main.py"], None)
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get(
                "/api/assistant/files",
                params={"path": ".", "pattern": "**/*.py", "recursive": True},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["files"] is not None

    def test_list_files_invalid_path(self, api_test_client: TestClient):
        """Test listing files with invalid path."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.list_files = AsyncMock(
                return_value=(None, "Path does not exist")
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get(
                "/api/assistant/files",
                params={"path": "/nonexistent"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["error"] is not None

    def test_read_file_success(self, api_test_client: TestClient):
        """Test reading a file."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.read_file = AsyncMock(
                return_value=("print('Hello World')", None)
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get(
                "/api/assistant/file",
                params={"path": "main.py"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "print('Hello World')"
            assert data["error"] is None

    def test_read_file_not_found(self, api_test_client: TestClient):
        """Test reading a non-existent file."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.read_file = AsyncMock(return_value=(None, "File not found"))
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get(
                "/api/assistant/file",
                params={"path": "nonexistent.py"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] is None
            assert data["error"] is not None

    def test_write_file_success(self, api_test_client: TestClient):
        """Test writing a file."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.write_file = AsyncMock(return_value=(True, None))
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/file",
                json={"path": "test.py", "content": "# Test file"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["error"] is None

    def test_write_file_permission_denied(self, api_test_client: TestClient):
        """Test writing file with permission error."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.write_file = AsyncMock(
                return_value=(False, "Permission denied")
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/file",
                json={"path": "/etc/passwd", "content": "malicious"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "denied" in data["error"].lower() or "Permission" in data["error"]


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantCommandAPI:
    """Tests for /api/assistant/execute endpoint."""

    def test_execute_allowed_command(self, api_test_client: TestClient):
        """Test executing an allowed command."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.command_sandbox.validate_command = MagicMock(
                return_value=(True, None, False)
            )
            mock_result = MagicMock()
            mock_result.status.value = "completed"
            mock_result.stdout = "file1.py\nfile2.py"
            mock_result.stderr = ""
            mock_result.exit_code = 0
            mock_agent.command_sandbox.execute = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/execute",
                json={"command": "ls -la"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["exit_code"] == 0

    def test_execute_blocked_command(self, api_test_client: TestClient):
        """Test executing a blocked command."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.command_sandbox.validate_command = MagicMock(
                return_value=(False, "Command not allowed", False)
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/execute",
                json={"command": "rm -rf /"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"

    def test_execute_requires_approval(self, api_test_client: TestClient):
        """Test command that requires approval."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.command_sandbox.validate_command = MagicMock(
                return_value=(True, None, True)  # requires_approval=True
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/execute",
                json={"command": "pip install something"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending_approval"
            assert data["requires_approval"] is True


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantSearchAPI:
    """Tests for /api/assistant/search endpoint."""

    def test_search_files_success(self, api_test_client: TestClient):
        """Test searching files."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.search_files = AsyncMock(
                return_value=(
                    [
                        {"file": "main.py", "line": 10, "content": "def test_func():"},
                        {"file": "utils.py", "line": 25, "content": "    test_func()"},
                    ],
                    None,
                )
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/search",
                json={"query": "test_func", "file_pattern": "*.py"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["matches"] is not None
            assert len(data["matches"]) == 2

    def test_search_no_results(self, api_test_client: TestClient):
        """Test search with no results."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.file_sandbox.search_files = AsyncMock(return_value=([], None))
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/search",
                json={"query": "nonexistent_function"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["matches"] == []


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantContextAPI:
    """Tests for /api/assistant/context endpoint."""

    def test_get_context(self, api_test_client: TestClient):
        """Test getting context information."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.get_context = AsyncMock(
                return_value={
                    "project_root": "/home/user/project",
                    "model": "llama3.2",
                    "message_count": 5,
                    "has_pyproject": True,
                    "src_dirs": ["src"],
                }
            )
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get("/api/assistant/context")

            assert response.status_code == 200
            data = response.json()
            assert "project_root" in data
            assert "model" in data
            assert "message_count" in data


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantResetAPI:
    """Tests for /api/assistant/reset endpoint."""

    def test_reset_conversation(self, api_test_client: TestClient):
        """Test resetting conversation history."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.reset = MagicMock()
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post("/api/assistant/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            mock_agent.reset.assert_called_once()


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantActionsAPI:
    """Tests for /api/assistant/action/* endpoints."""

    def test_approve_action(self, api_test_client: TestClient):
        """Test approving a pending action."""
        with patch(
            "ghoststorm.api.routes.assistant._pending_actions",
            {"test-id": {"type": "execute", "command": "ls"}},
        ):
            with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
                mock_agent = MagicMock()
                mock_result = MagicMock()
                mock_result.status.value = "completed"
                mock_result.stdout = "output"
                mock_result.stderr = ""
                mock_result.exit_code = 0
                mock_agent.command_sandbox.execute = AsyncMock(return_value=mock_result)
                mock_get_agent.return_value = mock_agent

                response = api_test_client.post(
                    "/api/assistant/action/approve",
                    json={"action_id": "test-id", "approved": True},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "executed"

    def test_reject_action(self, api_test_client: TestClient):
        """Test rejecting a pending action."""
        with patch(
            "ghoststorm.api.routes.assistant._pending_actions",
            {"test-id": {"type": "execute", "command": "ls"}},
        ):
            response = api_test_client.post(
                "/api/assistant/action/approve",
                json={"action_id": "test-id", "approved": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "rejected"

    def test_approve_nonexistent_action(self, api_test_client: TestClient):
        """Test approving non-existent action."""
        response = api_test_client.post(
            "/api/assistant/action/approve",
            json={"action_id": "nonexistent", "approved": True},
        )

        assert response.status_code == 404

    def test_get_pending_actions(self, api_test_client: TestClient):
        """Test getting pending actions."""
        with patch(
            "ghoststorm.api.routes.assistant._pending_actions", {"id1": {"type": "execute"}}
        ):
            response = api_test_client.get("/api/assistant/pending")

            assert response.status_code == 200
            data = response.json()
            assert "pending" in data


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantModelsAPI:
    """Tests for /api/assistant/models/* endpoints."""

    def test_list_models(self, api_test_client: TestClient, mock_ollama_service):
        """Test listing available models."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.config.model = "llama3.2"
            mock_agent.config.ollama_url = "http://localhost:11434"
            mock_get_agent.return_value = mock_agent

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "models": [
                        {"name": "llama3.2"},
                        {"name": "qwen2.5-coder:32b"},
                    ]
                }
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                response = api_test_client.get("/api/assistant/models")

                assert response.status_code == 200
                data = response.json()
                assert "models" in data
                assert "current" in data
                assert "recommended" in data

    def test_set_model(self, api_test_client: TestClient):
        """Test setting active model."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/models/set",
                params={"model": "qwen2.5-coder:32b"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["model"] == "qwen2.5-coder:32b"

    def test_delete_model(self, api_test_client: TestClient):
        """Test deleting a model."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.config.ollama_url = "http://localhost:11434"
            mock_get_agent.return_value = mock_agent

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
                    return_value=mock_response
                )

                response = api_test_client.delete("/api/assistant/models/test-model")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
class TestAssistantSettingsAPI:
    """Tests for /api/assistant/settings endpoints."""

    def test_get_settings(self, api_test_client: TestClient):
        """Test getting assistant settings."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.config.model = "llama3.2"
            mock_agent.config.temperature = 0.7
            mock_agent.config.max_tokens = 4096
            mock_agent.config.ollama_url = "http://localhost:11434"
            mock_agent.config.command_timeout = 30.0
            mock_get_agent.return_value = mock_agent

            response = api_test_client.get("/api/assistant/settings")

            assert response.status_code == 200
            data = response.json()
            assert "model" in data
            assert "temperature" in data
            assert "max_tokens" in data

    def test_update_settings(self, api_test_client: TestClient):
        """Test updating assistant settings."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.config.temperature = 0.7
            mock_agent.config.max_tokens = 4096
            mock_agent.config.command_timeout = 30.0
            mock_get_agent.return_value = mock_agent

            response = api_test_client.post(
                "/api/assistant/settings",
                params={"temperature": 0.9, "max_tokens": 8192},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_update_settings_with_bounds(self, api_test_client: TestClient):
        """Test settings are bounded correctly."""
        with patch("ghoststorm.api.routes.assistant._get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.config.temperature = 0.7
            mock_agent.config.max_tokens = 4096
            mock_agent.config.command_timeout = 30.0
            mock_get_agent.return_value = mock_agent

            # Temperature should be bounded 0-2
            response = api_test_client.post(
                "/api/assistant/settings",
                params={"temperature": 5.0},  # Out of range
            )

            assert response.status_code == 200
            # Should be clamped to max 2.0
            assert mock_agent.config.temperature == 2.0


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
@pytest.mark.docker
class TestAssistantDockerAPI:
    """Tests for /api/assistant/docker/* endpoints."""

    def test_get_docker_status_available(self, api_test_client: TestClient, mock_docker_service):
        """Test getting Docker status when available."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            # Docker version check
            mock_cmd.side_effect = [
                ("20.10.0", "", 0),  # docker version
                ("abc123|Up 5 minutes", "", 0),  # docker ps
            ]

            response = api_test_client.get("/api/assistant/docker/status")

            assert response.status_code == 200
            data = response.json()
            assert data["docker_available"] is True
            assert data["container_exists"] is True
            assert data["container_running"] is True

    def test_get_docker_status_not_installed(self, api_test_client: TestClient):
        """Test Docker status when not installed."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            mock_cmd.side_effect = FileNotFoundError("docker not found")

            response = api_test_client.get("/api/assistant/docker/status")

            assert response.status_code == 200
            data = response.json()
            assert data["docker_available"] is False
            assert "not installed" in data["error"].lower()

    def test_get_docker_status_not_running(self, api_test_client: TestClient):
        """Test Docker status when daemon not running."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            mock_cmd.return_value = ("", "Cannot connect to Docker daemon", 1)

            response = api_test_client.get("/api/assistant/docker/status")

            assert response.status_code == 200
            data = response.json()
            assert data["docker_available"] is False

    def test_start_docker_container(self, api_test_client: TestClient):
        """Test starting Ollama Docker container."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
                mock_status.return_value = MagicMock(
                    docker_available=True,
                    container_exists=False,
                    container_running=False,
                    error=None,
                )
                mock_cmd.return_value = ("", "", 0)

                response = api_test_client.post("/api/assistant/docker/start")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ["created", "started", "already_running"]

    def test_start_already_running(self, api_test_client: TestClient):
        """Test starting when container already running."""
        with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
            mock_status.return_value = MagicMock(
                docker_available=True,
                container_exists=True,
                container_running=True,
                error=None,
            )

            response = api_test_client.post("/api/assistant/docker/start")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_running"

    def test_stop_docker_container(self, api_test_client: TestClient):
        """Test stopping Ollama Docker container."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
                mock_status.return_value = MagicMock(
                    docker_available=True,
                    container_exists=True,
                    container_running=True,
                )
                mock_cmd.return_value = ("", "", 0)

                response = api_test_client.post("/api/assistant/docker/stop")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "stopped"

    def test_stop_already_stopped(self, api_test_client: TestClient):
        """Test stopping when already stopped."""
        with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
            mock_status.return_value = MagicMock(
                container_exists=True,
                container_running=False,
            )

            response = api_test_client.post("/api/assistant/docker/stop")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_stopped"

    def test_remove_docker_container(self, api_test_client: TestClient):
        """Test removing Ollama Docker container."""
        with patch("ghoststorm.api.routes.assistant._run_docker_command") as mock_cmd:
            with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
                mock_status.return_value = MagicMock(
                    container_exists=True,
                    container_running=False,
                )
                mock_cmd.return_value = ("", "", 0)

                response = api_test_client.delete("/api/assistant/docker/container")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "removed"

    def test_remove_nonexistent_container(self, api_test_client: TestClient):
        """Test removing non-existent container."""
        with patch("ghoststorm.api.routes.assistant.get_docker_status") as mock_status:
            mock_status.return_value = MagicMock(container_exists=False)

            response = api_test_client.delete("/api/assistant/docker/container")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.assistant
@pytest.mark.real
@pytest.mark.ollama
class TestAssistantRealOllama:
    """Real Ollama integration tests - require --run-real flag."""

    def test_real_chat_response(
        self,
        api_test_client: TestClient,
        ollama_url: str,
    ):
        """Test real chat with Ollama."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={"message": "Say 'hello' in one word only", "stream": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0

    def test_real_list_models(
        self,
        api_test_client: TestClient,
        ollama_url: str,
    ):
        """Test listing real Ollama models."""
        response = api_test_client.get("/api/assistant/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
