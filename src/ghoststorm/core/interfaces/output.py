"""Output writer interface definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IOutputWriter(Protocol):
    """Contract for output writers."""

    @property
    def name(self) -> str:
        """Writer name."""
        ...

    @property
    def format(self) -> str:
        """Output format (json, csv, sqlite, etc.)."""
        ...

    @property
    def records_written(self) -> int:
        """Number of records written."""
        ...

    async def initialize(
        self,
        output_path: Path | str,
        *,
        schema: dict[str, Any] | None = None,
        append: bool = False,
    ) -> None:
        """
        Initialize the writer.

        Args:
            output_path: Path to output file/database
            schema: Optional schema definition
            append: Whether to append to existing file
        """
        ...

    async def write(self, record: dict[str, Any]) -> None:
        """
        Write a single record.

        Args:
            record: Data record to write
        """
        ...

    async def write_many(self, records: list[dict[str, Any]]) -> None:
        """
        Write multiple records.

        Args:
            records: List of data records to write
        """
        ...

    async def write_screenshot(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write a screenshot.

        Args:
            data: Screenshot binary data
            filename: Optional filename (auto-generated if None)
            metadata: Optional metadata to store

        Returns:
            Path to saved screenshot
        """
        ...

    async def flush(self) -> None:
        """Flush any buffered data to disk."""
        ...

    async def close(self) -> None:
        """Close the writer and finalize output."""
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get writer statistics."""
        ...
