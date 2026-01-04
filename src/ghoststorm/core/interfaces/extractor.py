"""Data extractor interface definitions."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ghoststorm.core.interfaces.browser import IPage


@runtime_checkable
class IDataExtractor(Protocol):
    """Contract for data extractors."""

    @property
    def name(self) -> str:
        """Extractor name."""
        ...

    @property
    def selector_type(self) -> str:
        """Type of selector used (css, xpath, jsonld, regex)."""
        ...

    async def extract(
        self,
        page: IPage,
        selector: str,
        *,
        attribute: str | None = None,
        multiple: bool = False,
        default: Any = None,
    ) -> Any:
        """
        Extract data from page using selector.

        Args:
            page: The page to extract from
            selector: The selector expression
            attribute: Attribute to extract (None for text content)
            multiple: Whether to extract all matches or just first
            default: Default value if not found

        Returns:
            Extracted data (single value or list if multiple=True)
        """
        ...

    async def extract_many(
        self,
        page: IPage,
        selectors: dict[str, str],
        *,
        defaults: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Extract multiple fields at once.

        Args:
            page: The page to extract from
            selectors: Dict of field_name -> selector
            defaults: Default values for fields

        Returns:
            Dict of field_name -> extracted_value
        """
        ...

    async def extract_table(
        self,
        page: IPage,
        table_selector: str,
        *,
        headers: list[str] | None = None,
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> list[dict[str, Any]]:
        """
        Extract data from a table.

        Args:
            page: The page to extract from
            table_selector: Selector for the table element
            headers: Column headers (auto-detect if None)
            row_selector: Selector for rows within table
            cell_selector: Selector for cells within row

        Returns:
            List of dicts, one per row
        """
        ...

    async def exists(
        self,
        page: IPage,
        selector: str,
    ) -> bool:
        """Check if selector matches any element."""
        ...

    async def count(
        self,
        page: IPage,
        selector: str,
    ) -> int:
        """Count elements matching selector."""
        ...
