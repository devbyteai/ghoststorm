"""Credential storage for premium proxy providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CredentialStore:
    """Secure storage for provider credentials.

    Stores credentials in a JSON file. For production, consider:
    - Environment variables
    - HashiCorp Vault
    - AWS Secrets Manager
    - Encrypted file storage
    """

    def __init__(self, config_dir: Path | str = "data/config") -> None:
        """Initialize credential store.

        Args:
            config_dir: Directory to store credentials file
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._credentials_file = self.config_dir / "providers.json"
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load credentials from file."""
        if self._credentials_file.exists():
            try:
                content = self._credentials_file.read_text()
                self._cache = json.loads(content) if content.strip() else {}
                logger.debug(
                    "Loaded provider credentials",
                    providers=list(self._cache.keys()),
                )
            except Exception as e:
                logger.error("Failed to load credentials", error=str(e))
                self._cache = {}
        else:
            self._cache = {}

    def _save(self) -> None:
        """Save credentials to file."""
        try:
            self._credentials_file.write_text(
                json.dumps(self._cache, indent=2, default=str)
            )
            logger.debug("Saved provider credentials")
        except Exception as e:
            logger.error("Failed to save credentials", error=str(e))
            raise

    def save(self, provider: str, credentials: dict[str, Any]) -> None:
        """Save credentials for a provider.

        Args:
            provider: Provider name (e.g., 'decodo', 'brightdata')
            credentials: Credential dictionary
        """
        # Don't save None values
        clean_creds = {k: v for k, v in credentials.items() if v is not None}
        self._cache[provider] = clean_creds
        self._save()
        logger.info("Saved credentials", provider=provider)

    def get(self, provider: str) -> dict[str, Any] | None:
        """Get credentials for a provider.

        Args:
            provider: Provider name

        Returns:
            Credential dictionary or None if not found
        """
        return self._cache.get(provider)

    def remove(self, provider: str) -> bool:
        """Remove credentials for a provider.

        Args:
            provider: Provider name

        Returns:
            True if removed, False if not found
        """
        if provider in self._cache:
            del self._cache[provider]
            self._save()
            logger.info("Removed credentials", provider=provider)
            return True
        return False

    def list_providers(self) -> list[str]:
        """List all configured providers.

        Returns:
            List of provider names
        """
        return list(self._cache.keys())

    def is_configured(self, provider: str) -> bool:
        """Check if a provider is configured.

        Args:
            provider: Provider name

        Returns:
            True if configured
        """
        return provider in self._cache

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Get all configured providers.

        Returns:
            Dictionary of all providers and their credentials
        """
        # Return a copy to prevent mutation
        return dict(self._cache)

    def clear(self) -> None:
        """Remove all credentials."""
        self._cache = {}
        self._save()
        logger.info("Cleared all credentials")
