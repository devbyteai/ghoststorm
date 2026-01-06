"""Documentation API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger(__name__)

router = APIRouter()

# Path to docs directory (relative to project root)
# docs.py -> routes/ -> api/ -> ghoststorm/ -> src/ -> ghoststorm (project root)
DOCS_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs"


@router.get("")
async def list_docs() -> dict[str, Any]:
    """List all available documentation files."""
    try:
        if not DOCS_DIR.exists():
            return {"success": True, "docs": []}

        docs = []
        for file in sorted(DOCS_DIR.glob("*.md")):
            # Read first line for title
            title = file.stem.replace("-", " ").title()
            try:
                with open(file, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("# "):
                        title = first_line[2:]
            except Exception:
                pass

            docs.append(
                {
                    "filename": file.name,
                    "slug": file.stem,
                    "title": title,
                }
            )

        return {"success": True, "docs": docs}

    except Exception as e:
        logger.error("Failed to list docs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{filename}")
async def get_doc(filename: str) -> dict[str, Any]:
    """Get documentation file content."""
    try:
        # Ensure .md extension
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        file_path = DOCS_DIR / filename

        # Security check - no path traversal
        try:
            file_path = file_path.resolve()
            docs_dir = DOCS_DIR.resolve()
            if not str(file_path).startswith(str(docs_dir)):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid path")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Doc not found: {filename}")

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Extract title from first heading
        title = filename.replace(".md", "").replace("-", " ").title()
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return {
            "success": True,
            "filename": filename,
            "title": title,
            "content": content,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to read doc", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
