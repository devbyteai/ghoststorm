"""Data management API routes."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"


# ============ DATA LOADING UTILITIES ============
# These functions are used by task execution to load random data items


def get_random_user_agent(source_file: str | None = None) -> str | None:
    """Get a random user agent string from the data directory."""
    ua_dir = DATA_DIR / "user_agents"
    if not ua_dir.exists():
        return None

    # If source file specified, use it
    if source_file:
        file_path = ua_dir / source_file
        if file_path.exists():
            try:
                with open(file_path) as f:
                    lines = [line.strip() for line in f if line.strip()]
                    return random.choice(lines) if lines else None
            except Exception:
                pass

    # Otherwise, pick from any available file
    txt_files = list(ua_dir.glob("*.txt"))
    if not txt_files:
        return None

    try:
        # Pick a random file
        chosen_file = random.choice(txt_files)
        with open(chosen_file) as f:
            lines = [line.strip() for line in f if line.strip()]
            return random.choice(lines) if lines else None
    except Exception:
        return None


def get_random_fingerprint(source_file: str | None = None) -> dict[str, Any] | None:
    """Get a random browser fingerprint from the data directory."""
    fp_dir = DATA_DIR / "fingerprints"
    if not fp_dir.exists():
        return None

    # If source file specified, use it
    if source_file:
        file_path = fp_dir / source_file
        if file_path.exists():
            try:
                with open(file_path) as f:
                    if source_file.endswith(".json"):
                        data = json.load(f)
                        if isinstance(data, list):
                            return random.choice(data) if data else None
                        return data
                    else:
                        lines = [line.strip() for line in f if line.strip()]
                        if lines:
                            try:
                                return json.loads(random.choice(lines))
                            except Exception:
                                pass
            except Exception:
                pass

    # Otherwise, pick from any available file
    json_files = list(fp_dir.glob("*.json"))
    if json_files:
        try:
            chosen_file = random.choice(json_files)
            with open(chosen_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return random.choice(data) if data else None
                return data
        except Exception:
            pass

    return None


def get_random_screen_size() -> tuple[int, int] | None:
    """Get a random screen size (width, height) from the data directory."""
    screen_dir = DATA_DIR / "screen_sizes"
    if not screen_dir.exists():
        return None

    txt_files = list(screen_dir.glob("*.txt"))
    if not txt_files:
        # Default screen sizes if none available
        defaults = [(1920, 1080), (1366, 768), (1440, 900), (1536, 864), (390, 844)]
        return random.choice(defaults)

    try:
        chosen_file = random.choice(txt_files)
        with open(chosen_file) as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                size_str = random.choice(lines)
                # Parse "1920x1080" or "1920,1080" format
                if "x" in size_str:
                    w, h = size_str.split("x")
                elif "," in size_str:
                    w, h = size_str.split(",")
                else:
                    return None
                return (int(w.strip()), int(h.strip()))
    except Exception:
        pass

    return None


def get_random_referrer() -> str | None:
    """Get a random referrer URL from the data directory."""
    ref_dir = DATA_DIR / "referrers"
    if not ref_dir.exists():
        return None

    txt_files = list(ref_dir.glob("*.txt"))
    if not txt_files:
        return None

    try:
        chosen_file = random.choice(txt_files)
        with open(chosen_file) as f:
            lines = [line.strip() for line in f if line.strip()]
            return random.choice(lines) if lines else None
    except Exception:
        return None


def get_evasion_scripts() -> list[str]:
    """Get all evasion scripts from the data directory."""
    evasion_dir = DATA_DIR / "evasion"
    if not evasion_dir.exists():
        return []

    scripts = []
    for js_file in evasion_dir.glob("*.js"):
        try:
            with open(js_file) as f:
                scripts.append(f.read())
        except Exception:
            pass

    return scripts


def get_random_proxy() -> str | None:
    """Get a random proxy from the alive proxies file."""
    proxy_file = DATA_DIR / "proxies" / "alive_proxies.txt"
    if not proxy_file.exists():
        return None

    try:
        with open(proxy_file) as f:
            lines = [line.strip() for line in f if line.strip()]
            return random.choice(lines) if lines else None
    except Exception:
        return None


def load_all_proxies() -> list[str]:
    """Load all proxies from the proxies directory."""
    proxy_dir = DATA_DIR / "proxies"
    if not proxy_dir.exists():
        return []

    proxies = []
    for txt_file in proxy_dir.glob("*.txt"):
        try:
            with open(txt_file) as f:
                proxies.extend([line.strip() for line in f if line.strip()])
        except Exception:
            pass

    return proxies


# Category mappings
CATEGORY_DIRS = {
    "user_agents": "user_agents",
    "fingerprints": "fingerprints",
    "referrers": "referrers",
    "blacklists": "blacklists",
    "screen_sizes": "screen_sizes",
    "behavior": "behavior",
    "evasion": "evasion",
}


class DataItem(BaseModel):
    content: str


class DataItemUpdate(BaseModel):
    old_content: str
    new_content: str


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file."""
    if not file_path.exists():
        return 0
    try:
        with open(file_path) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def count_json_items(file_path: Path) -> int:
    """Count items in a JSON file (if it's a list)."""
    if not file_path.exists():
        return 0
    try:
        import json

        with open(file_path) as f:
            data = json.load(f)
            if isinstance(data, (list, dict)):
                return len(data)
            return 1
    except Exception:
        return 0


def count_dir_entries(dir_path: Path, pattern: str = "*.txt") -> int:
    """Count total lines across all files in a directory."""
    if not dir_path.exists():
        return 0
    total = 0
    for f in dir_path.glob(pattern):
        total += count_lines(f)
    # Also count JSON files
    for f in dir_path.glob("*.json"):
        total += count_json_items(f)
    return total


@router.get("/stats")
async def get_data_stats() -> dict:
    """Get data statistics."""
    return {
        "user_agents": count_dir_entries(DATA_DIR / "user_agents"),
        "fingerprints": count_dir_entries(DATA_DIR / "fingerprints"),
        "referrers": count_dir_entries(DATA_DIR / "referrers"),
        "blacklists": count_dir_entries(DATA_DIR / "blacklists"),
        "screen_sizes": count_dir_entries(DATA_DIR / "screen_sizes"),
        "behavior": count_dir_entries(DATA_DIR / "behavior"),
        "evasion": count_dir_entries(DATA_DIR / "evasion"),
    }


def get_category_dir(category: str) -> Path:
    """Get the directory path for a category."""
    if category not in CATEGORY_DIRS:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    return DATA_DIR / CATEGORY_DIRS[category]


def read_data_items(category: str) -> dict:
    """Read all data items from a category directory."""
    dir_path = get_category_dir(category)
    result = {"files": [], "items": []}

    if not dir_path.exists():
        return result

    # Read text files
    for f in sorted(dir_path.glob("*.txt")):
        try:
            with open(f) as file:
                lines = [line.strip() for line in file if line.strip()]
                result["files"].append(
                    {
                        "name": f.name,
                        "type": "txt",
                        "count": len(lines),
                        "items": lines[:100],  # Limit to first 100 for UI
                    }
                )
        except Exception:
            pass

    # Read JSON files
    for f in sorted(dir_path.glob("*.json")):
        try:
            with open(f) as file:
                data = json.load(file)
                if isinstance(data, list):
                    result["files"].append(
                        {"name": f.name, "type": "json", "count": len(data), "items": data[:100]}
                    )
                elif isinstance(data, dict):
                    result["files"].append(
                        {
                            "name": f.name,
                            "type": "json",
                            "count": len(data),
                            "items": list(data.keys())[:100],
                        }
                    )
        except Exception:
            pass

    return result


# ============ USER AGENT GENERATION ENDPOINTS ============
# NOTE: These specific routes MUST be defined BEFORE the generic /{category}/{filename} routes
# to avoid path parameter matching issues in FastAPI.


class UAGenerateRequest(BaseModel):
    """Request for dynamic UA generation."""

    browser: str = "chrome"
    os: str = "windows"
    count: int = 1


class UAParseRequest(BaseModel):
    """Request to parse a user agent string."""

    user_agent: str


@router.post("/user_agents/generate")
async def generate_user_agent(request: UAGenerateRequest) -> dict:
    """Generate fresh user agent(s) using browserforge."""
    try:
        from browserforge.headers import HeaderGenerator

        # Allow up to 500 per request for bulk generation
        count = min(request.count, 500)
        results = []

        # Create generator once for efficiency
        hg = HeaderGenerator(browser=request.browser, os=request.os)

        for _ in range(count):
            headers = hg.generate()
            results.append(
                {
                    "user_agent": headers.get("User-Agent", ""),
                    "sec_ch_ua": headers.get("sec-ch-ua", ""),
                    "sec_ch_ua_platform": headers.get("sec-ch-ua-platform", ""),
                    "sec_ch_ua_mobile": headers.get("sec-ch-ua-mobile", ""),
                    "accept_language": headers.get("Accept-Language", ""),
                }
            )

        return {
            "success": True,
            "user_agents": results,
            "browser": request.browser,
            "os": request.os,
            "count": len(results),
        }
    except ImportError:
        return {"success": False, "error": "browserforge not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/user_agents/parse")
async def parse_user_agent(request: UAParseRequest) -> dict:
    """Parse a user agent string to extract browser/OS info."""
    ua = request.user_agent

    # Simple parsing logic
    browser = "Unknown"
    os_name = "Unknown"
    device = "Desktop"

    # Detect browser
    if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua:
        browser = "Chrome"
    elif "Firefox" in ua:
        browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Edg" in ua:
        browser = "Edge"
    elif "OPR" in ua or "Opera" in ua:
        browser = "Opera"

    # Detect OS
    if "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Linux" in ua and "Android" not in ua:
        os_name = "Linux"
    elif "Android" in ua:
        os_name = "Android"
        device = "Mobile"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
        device = "Mobile" if "iPhone" in ua else "Tablet"

    # Detect if WebView/In-App
    if "wv" in ua.lower() or "WebView" in ua:
        device = "WebView"
    if "TikTok" in ua or "BytedanceWebview" in ua:
        device = "TikTok WebView"
    if "Instagram" in ua:
        device = "Instagram WebView"

    return {
        "user_agent": ua,
        "browser": browser,
        "os": os_name,
        "device": device,
    }


@router.get("/user_agents/sample/{filename}")
async def sample_user_agent(filename: str) -> dict:
    """Get a random sample from a user agent file."""
    ua_dir = DATA_DIR / "user_agents"
    file_path = ua_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        if not lines:
            return {"success": False, "error": "No user agents in file"}

        ua = random.choice(lines)

        # Parse the selected UA
        parse_result = await parse_user_agent(UAParseRequest(user_agent=ua))

        return {
            "success": True,
            "user_agent": ua,
            "browser": parse_result["browser"],
            "os": parse_result["os"],
            "device": parse_result["device"],
            "file": filename,
            "total_in_file": len(lines),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Platform-specific UA recommendations
PLATFORM_UA_RECOMMENDATIONS = {
    "tiktok": {
        "recommended_file": "tiktok_inapp.txt",
        "recommended_mode": "file",
        "message": "TikTok works best with in-app WebView user agents",
        "settings": {"browser": "chrome", "os": "android", "include_webview": True},
    },
    "instagram": {
        "recommended_file": "instagram_inapp.txt",
        "recommended_mode": "file",
        "message": "Instagram works best with in-app WebView user agents",
        "settings": {"browser": "chrome", "os": "android", "include_webview": True},
    },
    "youtube": {
        "recommended_file": "youtube_inapp.txt",
        "recommended_mode": "dynamic",
        "message": "YouTube works well with modern Chrome user agents",
        "settings": {"browser": "chrome", "os": "windows", "include_mobile": True},
    },
    "dextools": {
        "recommended_file": "aggregated.txt",
        "recommended_mode": "dynamic",
        "message": "DEXTools works best with desktop Chrome/Firefox",
        "settings": {"browser": "chrome", "os": "windows", "include_mobile": False},
    },
    "generic": {
        "recommended_file": "aggregated.txt",
        "recommended_mode": "dynamic",
        "message": "Using dynamic Chrome user agents for best compatibility",
        "settings": {"browser": "chrome", "os": "windows", "include_mobile": False},
    },
}


@router.get("/user_agents/recommendation/{platform}")
async def get_ua_recommendation(platform: str) -> dict:
    """Get user agent recommendations for a specific platform."""
    platform = platform.lower()

    if platform not in PLATFORM_UA_RECOMMENDATIONS:
        platform = "generic"

    rec = PLATFORM_UA_RECOMMENDATIONS[platform]

    # Check if recommended file exists
    ua_dir = DATA_DIR / "user_agents"
    file_exists = (ua_dir / rec["recommended_file"]).exists()

    # Count UAs in file if exists
    file_count = 0
    if file_exists:
        try:
            with open(ua_dir / rec["recommended_file"]) as f:
                file_count = sum(1 for line in f if line.strip() and not line.startswith("#"))
        except Exception:
            pass

    return {
        "platform": platform,
        "recommended_mode": rec["recommended_mode"],
        "recommended_file": rec["recommended_file"],
        "file_exists": file_exists,
        "file_count": file_count,
        "message": rec["message"],
        "settings": rec["settings"],
    }


# ============ FINGERPRINT GENERATION ENDPOINTS ============


class FPGenerateRequest(BaseModel):
    """Request for dynamic fingerprint generation."""

    browser: str = "chrome"
    os: str = "windows"
    count: int = 1


@router.post("/fingerprints/generate")
async def generate_fingerprint(request: FPGenerateRequest) -> dict:
    """Generate browser fingerprint(s) using browserforge."""
    try:
        from browserforge.fingerprints import FingerprintGenerator

        count = min(request.count, 100)  # Max 100 per request (FPs are heavier)
        results = []

        fg = FingerprintGenerator(browser=request.browser, os=request.os)

        for _ in range(count):
            fp = fg.generate()

            # Extract key fingerprint data
            results.append(
                {
                    "screen": {
                        "width": fp.screen.width,
                        "height": fp.screen.height,
                        "availWidth": fp.screen.availWidth,
                        "availHeight": fp.screen.availHeight,
                        "colorDepth": fp.screen.colorDepth,
                        "pixelRatio": fp.screen.devicePixelRatio,
                    },
                    "navigator": {
                        "userAgent": fp.navigator.userAgent,
                        "platform": fp.navigator.platform,
                        "language": fp.navigator.language,
                        "languages": fp.navigator.languages,
                        "hardwareConcurrency": fp.navigator.hardwareConcurrency,
                        "deviceMemory": fp.navigator.deviceMemory,
                        "maxTouchPoints": fp.navigator.maxTouchPoints,
                    },
                    "videoCard": {
                        "vendor": fp.videoCard.vendor if fp.videoCard else None,
                        "renderer": fp.videoCard.renderer if fp.videoCard else None,
                    },
                    "fonts": fp.fonts[:20] if fp.fonts else [],  # Limit fonts
                    "audioCodecs": fp.audioCodecs,
                    "videoCodecs": fp.videoCodecs,
                }
            )

        return {
            "success": True,
            "fingerprints": results,
            "browser": request.browser,
            "os": request.os,
            "count": len(results),
        }
    except ImportError:
        return {"success": False, "error": "browserforge not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/fingerprints/sample")
async def sample_fingerprint() -> dict:
    """Get a random sample from the fingerprints file."""
    fp_file = DATA_DIR / "fingerprints" / "devices.json"

    if not fp_file.exists():
        return {"success": False, "error": "Fingerprints file not found"}

    try:
        with open(fp_file) as f:
            data = json.load(f)

        if not data:
            return {"success": False, "error": "No fingerprints in file"}

        fp = random.choice(data)

        return {
            "success": True,
            "fingerprint": fp,
            "total_in_file": len(data),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ GENERATE AND SAVE ENDPOINT ============


class GenerateAndSaveRequest(BaseModel):
    """Request for generating data and saving to file."""

    count: int = 100
    browser: str = "chrome"  # For UA/fingerprints
    os: str = "windows"  # For UA/fingerprints
    target_file: str = ""  # Target filename


# Preset data for screen sizes and referrers
SCREEN_SIZE_PRESETS = [
    "1920x1080",
    "1366x768",
    "1536x864",
    "1440x900",
    "1280x720",
    "2560x1440",
    "3840x2160",
    "1600x900",
    "1280x800",
    "1024x768",
    # Mobile
    "390x844",
    "412x915",
    "360x800",
    "414x896",
    "375x812",
    "428x926",
    "393x873",
    "360x780",
    "412x892",
    "384x854",
]

REFERRER_PRESETS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=",
    "https://www.facebook.com/",
    "https://twitter.com/",
    "https://t.co/",
    "https://www.instagram.com/",
    "https://www.reddit.com/",
    "https://www.youtube.com/",
    "https://www.tiktok.com/",
    "https://www.linkedin.com/",
    "https://www.pinterest.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.yahoo.com/",
    "https://www.twitch.tv/",
    "https://discord.com/",
    "https://telegram.org/",
    "https://medium.com/",
    "https://www.quora.com/",
    "https://news.ycombinator.com/",
]


@router.post("/{category}/generate-and-save")
async def generate_and_save(category: str, request: GenerateAndSaveRequest) -> dict:
    """Generate data items and save them to a file."""
    if category not in ["user_agents", "fingerprints", "screen_sizes", "referrers"]:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category}' does not support generation",
        )

    dir_path = get_category_dir(category)
    dir_path.mkdir(parents=True, exist_ok=True)

    count = min(request.count, 500)  # Max 500 per request
    generated_items = []

    try:
        if category == "user_agents":
            # Generate using browserforge
            from browserforge.headers import HeaderGenerator

            target_file = request.target_file or "generated.txt"
            file_path = dir_path / target_file

            hg = HeaderGenerator(browser=request.browser, os=request.os)
            for _ in range(count):
                headers = hg.generate()
                ua = headers.get("User-Agent", "")
                if ua:
                    generated_items.append(ua)

            # Append to file
            with open(file_path, "a") as f:
                for item in generated_items:
                    f.write(item + "\n")

        elif category == "fingerprints":
            # Generate using browserforge
            from browserforge.fingerprints import FingerprintGenerator

            target_file = request.target_file or "generated.json"
            if not target_file.endswith(".json"):
                target_file += ".json"
            file_path = dir_path / target_file

            fg = FingerprintGenerator(browser=request.browser, os=request.os)
            for _ in range(count):
                fp = fg.generate()
                generated_items.append(
                    {
                        "screen": {
                            "width": fp.screen.width,
                            "height": fp.screen.height,
                            "availWidth": fp.screen.availWidth,
                            "availHeight": fp.screen.availHeight,
                            "colorDepth": fp.screen.colorDepth,
                            "pixelRatio": fp.screen.devicePixelRatio,
                        },
                        "navigator": {
                            "userAgent": fp.navigator.userAgent,
                            "platform": fp.navigator.platform,
                            "language": fp.navigator.language,
                            "languages": fp.navigator.languages,
                            "hardwareConcurrency": fp.navigator.hardwareConcurrency,
                            "deviceMemory": fp.navigator.deviceMemory,
                            "maxTouchPoints": fp.navigator.maxTouchPoints,
                        },
                        "videoCard": {
                            "vendor": fp.videoCard.vendor if fp.videoCard else None,
                            "renderer": fp.videoCard.renderer if fp.videoCard else None,
                        },
                    }
                )

            # Load existing data and append
            existing = []
            if file_path.exists():
                with open(file_path) as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = [existing]

            existing.extend(generated_items)
            with open(file_path, "w") as f:
                json.dump(existing, f, indent=2)

        elif category == "screen_sizes":
            # Use presets
            target_file = request.target_file or "generated.txt"
            file_path = dir_path / target_file

            # Generate random selections from presets
            for _ in range(count):
                generated_items.append(random.choice(SCREEN_SIZE_PRESETS))

            # Append to file
            with open(file_path, "a") as f:
                for item in generated_items:
                    f.write(item + "\n")

        elif category == "referrers":
            # Use presets
            target_file = request.target_file or "generated.txt"
            file_path = dir_path / target_file

            # Generate random selections from presets
            for _ in range(count):
                generated_items.append(random.choice(REFERRER_PRESETS))

            # Append to file
            with open(file_path, "a") as f:
                for item in generated_items:
                    f.write(item + "\n")

        # Get new total count
        new_total = count_dir_entries(dir_path)

        return {
            "success": True,
            "generated": len(generated_items),
            "saved_to": target_file,
            "new_total": new_total,
            "category": category,
        }

    except ImportError as e:
        return {"success": False, "error": f"Required library not installed: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ GENERIC CATEGORY/FILE ENDPOINTS ============
# NOTE: These generic routes MUST come AFTER the specific routes above


@router.get("/{category}")
async def list_data_items(category: str, limit: int = 100, offset: int = 0) -> dict:
    """List data items for a category."""
    return read_data_items(category)


@router.get("/{category}/{filename}")
async def get_file_content(category: str, filename: str) -> dict:
    """Get full content of a specific file."""
    dir_path = get_category_dir(category)
    file_path = dir_path / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure file is within the category directory
    try:
        file_path.resolve().relative_to(dir_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        if filename.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
                return {"type": "json", "data": data}
        else:
            with open(file_path) as f:
                lines = [line.strip() for line in f if line.strip()]
                return {"type": "txt", "data": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{category}/{filename}")
async def add_data_item(category: str, filename: str, item: DataItem) -> dict:
    """Add a new item to a data file."""
    dir_path = get_category_dir(category)
    file_path = dir_path / filename

    # Security check
    try:
        file_path.resolve().relative_to(dir_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Ensure directory exists
    dir_path.mkdir(parents=True, exist_ok=True)

    try:
        if filename.endswith(".json"):
            # Handle JSON files
            data = []
            if file_path.exists():
                with open(file_path) as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]
            data.append(item.content)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            # Handle text files - append new line
            with open(file_path, "a") as f:
                f.write(item.content.strip() + "\n")

        return {"success": True, "message": "Item added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{category}/{filename}")
async def delete_data_item(category: str, filename: str, item: DataItem) -> dict:
    """Delete an item from a data file."""
    dir_path = get_category_dir(category)
    file_path = dir_path / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security check
    try:
        file_path.resolve().relative_to(dir_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        if filename.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
            if isinstance(data, list) and item.content in data:
                data.remove(item.content)
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
        else:
            with open(file_path) as f:
                lines = [line.strip() for line in f if line.strip()]
            if item.content in lines:
                lines.remove(item.content)
                with open(file_path, "w") as f:
                    f.write("\n".join(lines) + "\n" if lines else "")

        return {"success": True, "message": "Item deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
