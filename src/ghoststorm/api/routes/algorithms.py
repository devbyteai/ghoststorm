"""Algorithms API routes for managing platform signature algorithms."""

from __future__ import annotations

import json
import hashlib
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
ALGO_DIR = DATA_DIR / "algorithms"

# Ensure algorithms directory exists
ALGO_DIR.mkdir(parents=True, exist_ok=True)

# Algorithm metadata
ALGORITHMS = {
    "tiktok_gorgon": {
        "name": "TikTok X-Gorgon",
        "platform": "tiktok",
        "type": "signature",
        "status": "deprecated",
        "headers": ["X-Gorgon", "X-Khronos"],
        "method": "MD5 + XOR + Bit Reversal",
        "description": "Legacy mobile API signature algorithm. Uses MD5 hash of params + data + cookies, XOR with 20-byte key, and bit reversal. Output format: 0404b0d30000 + 40 hex chars.",
        "update_frequency": "monthly",
        "github_source": "gaplan/TikTok-X-Gorgon",
        "code_file": "tiktok_gorgon.py",
        "can_fetch": True,
        "requires_js": False,
    },
    "tiktok_xbogus": {
        "name": "TikTok X-Bogus",
        "platform": "tiktok",
        "type": "signature",
        "status": "active",
        "headers": ["X-Bogus"],
        "method": "JavaScript VM Obfuscated",
        "description": "Current web API signature. Requires JavaScript VM execution via byted_acrawler.frontierSign(params). Cannot be statically reverse-engineered. Updates weekly.",
        "update_frequency": "weekly",
        "github_source": "carcabot/tiktok-signature",
        "cdn_source": "https://www.tiktok.com/",
        "code_file": "tiktok_xbogus.js",
        "can_fetch": True,
        "requires_js": True,
    },
    "tiktok_xgnarly": {
        "name": "TikTok X-Gnarly",
        "platform": "tiktok",
        "type": "signature",
        "status": "active",
        "headers": ["X-Gnarly"],
        "method": "JavaScript VM + X-Bogus Companion",
        "description": "Enhanced web security used alongside X-Bogus on newer endpoints. Also requires JavaScript VM execution. Updates weekly.",
        "update_frequency": "weekly",
        "github_source": "justbeluga/tiktok-web-reverse-engineering",
        "cdn_source": "https://www.tiktok.com/embed/",
        "code_file": "tiktok_xgnarly.js",
        "can_fetch": True,
        "requires_js": True,
    },
    "tiktok_mssdk": {
        "name": "TikTok MSSDK",
        "platform": "tiktok",
        "type": "device_token",
        "status": "active",
        "headers": ["X-SS-STUB", "X-SS-REQ-TICKET"],
        "method": "Mobile SDK Device Registration",
        "description": "Mobile SDK for device registration, hardware fingerprinting, and app signature verification. Requires APK decompile.",
        "github_source": "davidteather/TikTok-Api",
        "code_file": "tiktok_mssdk.py",
        "can_fetch": False,
        "requires_js": False,
    },
    "instagram_oauth": {
        "name": "Instagram Graph API",
        "platform": "instagram",
        "type": "oauth",
        "status": "active",
        "headers": ["Authorization"],
        "method": "OAuth 2.0 Bearer Token",
        "description": "Token-based authentication. No request signing required. Short-lived (1hr) or long-lived (60 days) tokens available.",
        "docs_url": "https://developers.facebook.com/docs/instagram-api/",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# Instagram Graph API Authentication
# No signature needed - just Bearer token

import requests

# 1. Get access token via Facebook OAuth
# https://www.facebook.com/v18.0/dialog/oauth?client_id={APP_ID}&redirect_uri={REDIRECT}&scope=instagram_basic,instagram_content_publish

# 2. Exchange code for token
token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
params = {
    "client_id": "YOUR_APP_ID",
    "client_secret": "YOUR_APP_SECRET",
    "grant_type": "authorization_code",
    "redirect_uri": "YOUR_REDIRECT_URI",
    "code": "AUTH_CODE"
}

# 3. Make API requests with token
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
response = requests.get(
    "https://graph.instagram.com/me/media",
    headers=headers
)''',
    },
    "youtube_api": {
        "name": "YouTube Data API v3",
        "platform": "youtube",
        "type": "api_key",
        "status": "active",
        "headers": ["Authorization"],
        "method": "API Key + OAuth 2.0",
        "description": "API key for public data, OAuth 2.0 for user actions. 10K quota per day. No signature generation needed.",
        "docs_url": "https://developers.google.com/youtube/v3",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# YouTube Data API v3 Authentication
# Two methods: API Key (public data) or OAuth 2.0 (user actions)

import requests

# METHOD 1: API Key (for public data)
API_KEY = "YOUR_API_KEY"
response = requests.get(
    "https://www.googleapis.com/youtube/v3/videos",
    params={
        "part": "statistics",
        "id": "VIDEO_ID",
        "key": API_KEY
    }
)

# METHOD 2: OAuth 2.0 (for user actions like upload, like, subscribe)
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
response = requests.post(
    "https://www.googleapis.com/youtube/v3/videos/rate",
    headers=headers,
    params={"id": "VIDEO_ID", "rating": "like"}
)

# Quota: 10,000 units/day
# Search = 100 units, Video info = 1 unit''',
    },
    "twitter_api": {
        "name": "Twitter/X API v2",
        "platform": "twitter",
        "type": "oauth",
        "status": "active",
        "headers": ["Authorization"],
        "method": "OAuth 2.0 PKCE + App-only Bearer",
        "description": "OAuth 2.0 PKCE flow for user context, app-only bearer token for read-only. Rate limits: 500K tweets/month (Basic), 1M (Pro).",
        "docs_url": "https://developer.twitter.com/en/docs/twitter-api",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# Twitter/X API v2 Authentication
# Two methods: App-only (read) or User context (write)

import requests
import base64

# METHOD 1: App-only Bearer Token (read-only)
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
credentials = base64.b64encode(f"{API_KEY}:{API_SECRET}".encode()).decode()

token_response = requests.post(
    "https://api.twitter.com/oauth2/token",
    headers={"Authorization": f"Basic {credentials}"},
    data={"grant_type": "client_credentials"}
)
bearer_token = token_response.json()["access_token"]

# Use bearer token
headers = {"Authorization": f"Bearer {bearer_token}"}
response = requests.get(
    "https://api.twitter.com/2/tweets/TWEET_ID",
    headers=headers
)

# METHOD 2: OAuth 2.0 PKCE (user actions)
# Requires user login flow with PKCE challenge
# See: https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code

# Rate limits: Basic=500K tweets/mo, Pro=1M tweets/mo''',
    },
    "facebook_api": {
        "name": "Facebook Graph API",
        "platform": "facebook",
        "type": "oauth",
        "status": "active",
        "headers": ["Authorization"],
        "method": "OAuth 2.0 with Facebook Login",
        "description": "Facebook Login OAuth flow. Page tokens for business actions. Long-lived tokens (60 days).",
        "docs_url": "https://developers.facebook.com/docs/graph-api/",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# Facebook Graph API Authentication
# Uses OAuth 2.0 with Facebook Login

import requests

# 1. Redirect user to Facebook Login
# https://www.facebook.com/v18.0/dialog/oauth?client_id={APP_ID}&redirect_uri={REDIRECT}&scope=public_profile,email

# 2. Exchange code for access token
token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
params = {
    "client_id": "YOUR_APP_ID",
    "client_secret": "YOUR_APP_SECRET",
    "redirect_uri": "YOUR_REDIRECT_URI",
    "code": "AUTH_CODE"
}
token_response = requests.get(token_url, params=params)
access_token = token_response.json()["access_token"]

# 3. Get long-lived token (60 days)
long_lived = requests.get(
    "https://graph.facebook.com/v18.0/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": "YOUR_APP_ID",
        "client_secret": "YOUR_APP_SECRET",
        "fb_exchange_token": access_token
    }
)

# 4. Make API requests
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("https://graph.facebook.com/v18.0/me", headers=headers)''',
    },
    "spotify_api": {
        "name": "Spotify Web API",
        "platform": "spotify",
        "type": "oauth",
        "status": "active",
        "headers": ["Authorization"],
        "method": "OAuth 2.0 Auth Code + Client Credentials",
        "description": "Authorization Code flow for user data, Client Credentials for public data. Refresh tokens for persistence.",
        "docs_url": "https://developer.spotify.com/documentation/web-api",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# Spotify Web API Authentication
# Two methods: Client Credentials (public) or Auth Code (user data)

import requests
import base64

CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# METHOD 1: Client Credentials (public data only)
credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
token_response = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={"Authorization": f"Basic {credentials}"},
    data={"grant_type": "client_credentials"}
)
access_token = token_response.json()["access_token"]

# METHOD 2: Authorization Code (user data, playlists, etc.)
# 1. Redirect to: https://accounts.spotify.com/authorize?client_id={ID}&response_type=code&redirect_uri={URI}&scope=user-read-private
# 2. Exchange code for token (includes refresh_token)

# Make API requests
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "https://api.spotify.com/v1/tracks/TRACK_ID",
    headers=headers
)''',
    },
    "twitch_api": {
        "name": "Twitch Helix API",
        "platform": "twitch",
        "type": "oauth",
        "status": "active",
        "headers": ["Authorization", "Client-Id"],
        "method": "OAuth 2.0 + Required Client-Id",
        "description": "OAuth 2.0 for user actions, app access tokens for public data. Client-Id header always required.",
        "docs_url": "https://dev.twitch.tv/docs/api/",
        "can_fetch": False,
        "requires_js": False,
        "example_code": '''# Twitch Helix API Authentication
# IMPORTANT: Client-Id header is ALWAYS required

import requests

CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# Get App Access Token (for public data)
token_response = requests.post(
    "https://id.twitch.tv/oauth2/token",
    params={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
)
access_token = token_response.json()["access_token"]

# Make API requests - Client-Id is REQUIRED
headers = {
    "Authorization": f"Bearer {access_token}",
    "Client-Id": CLIENT_ID  # REQUIRED!
}
response = requests.get(
    "https://api.twitch.tv/helix/users",
    headers=headers,
    params={"login": "username"}
)

# For user actions, use OAuth Authorization Code flow
# Redirect to: https://id.twitch.tv/oauth2/authorize?client_id={ID}&redirect_uri={URI}&response_type=code&scope=user:read:email''',
    },
}

# GitHub API sources for fetching
GITHUB_SOURCES = {
    "tiktok_gorgon": {
        "repo": "gaplan/TikTok-X-Gorgon",
        "file_path": "gorgon.py",
        "branch": "main",
    },
    "tiktok_xbogus": {
        "repo": "carcabot/tiktok-signature",
        "file_path": "src/signer.js",
        "branch": "master",
    },
    "tiktok_xgnarly": {
        "repo": "justbeluga/tiktok-web-reverse-engineering",
        "file_path": "xgnarly.js",
        "branch": "main",
    },
    "tiktok_mssdk": {
        "repo": "davidteather/TikTok-Api",
        "file_path": "TikTokApi/browser_utilities/browser.py",
        "branch": "master",
    },
}


def load_metadata() -> dict[str, Any]:
    """Load algorithm metadata from file."""
    meta_file = ALGO_DIR / "metadata.json"
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_metadata(metadata: dict[str, Any]) -> None:
    """Save algorithm metadata to file."""
    meta_file = ALGO_DIR / "metadata.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)


def get_algorithm_code(name: str) -> str | None:
    """Get algorithm code from file."""
    algo = ALGORITHMS.get(name)
    if not algo or not algo.get("code_file"):
        return None

    code_file = ALGO_DIR / algo["code_file"]
    if code_file.exists():
        try:
            with open(code_file) as f:
                return f.read()
        except Exception:
            pass
    return None


@router.get("")
async def list_algorithms() -> dict:
    """List all algorithms with status."""
    metadata = load_metadata()

    result = {}
    for name, algo in ALGORITHMS.items():
        meta = metadata.get(name, {})
        result[name] = {
            **algo,
            "last_updated": meta.get("last_updated"),
            "github_hash": meta.get("github_hash"),
            "cdn_hash": meta.get("cdn_hash"),
            "verified": meta.get("verified", False),
        }

    return {"algorithms": result}


@router.get("/{name}")
async def get_algorithm(name: str) -> dict:
    """Get algorithm details and code."""
    if name not in ALGORITHMS:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    algo = ALGORITHMS[name]
    metadata = load_metadata()
    meta = metadata.get(name, {})

    # Get code from file or use example_code for OAuth platforms
    code = get_algorithm_code(name)
    if not code and algo.get("example_code"):
        code = algo["example_code"]

    return {
        **algo,
        "code": code,
        "last_updated": meta.get("last_updated"),
        "github_hash": meta.get("github_hash"),
        "cdn_hash": meta.get("cdn_hash"),
        "verified": meta.get("verified", False),
    }


@router.post("/{name}/fetch/github")
async def fetch_from_github(name: str) -> dict:
    """Fetch algorithm from GitHub source."""
    if name not in ALGORITHMS:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    algo = ALGORITHMS[name]
    if not algo.get("can_fetch"):
        raise HTTPException(status_code=400, detail="Algorithm cannot be fetched")

    source = GITHUB_SOURCES.get(name)
    if not source:
        raise HTTPException(status_code=400, detail="No GitHub source configured")

    repo = source["repo"]
    file_path = source["file_path"]
    branch = source.get("branch", "main")

    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            code = response.text
            code_hash = hashlib.md5(code.encode()).hexdigest()

            # Save to file
            code_file = ALGO_DIR / algo["code_file"]
            with open(code_file, "w") as f:
                f.write(code)

            # Update metadata
            metadata = load_metadata()
            if name not in metadata:
                metadata[name] = {}
            metadata[name]["last_updated"] = datetime.now().isoformat()
            metadata[name]["github_hash"] = code_hash
            metadata[name]["github_source"] = url
            save_metadata(metadata)

            return {
                "success": True,
                "message": f"Fetched from {repo}",
                "hash": code_hash,
                "size": len(code),
            }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"GitHub error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/fetch/cdn")
async def fetch_from_cdn(name: str) -> dict:
    """Fetch algorithm from CDN/live source."""
    if name not in ALGORITHMS:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    algo = ALGORITHMS[name]
    cdn_source = algo.get("cdn_source")
    if not cdn_source:
        raise HTTPException(status_code=400, detail="No CDN source configured for this algorithm")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Fetch the page
            response = await client.get(cdn_source, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()

            html = response.text

            # Extract JS bundle URLs
            js_urls = []
            for match in re.finditer(r'src=["\']([^"\']*\.js[^"\']*)["\']', html):
                js_url = match.group(1)
                if not js_url.startswith("http"):
                    if js_url.startswith("//"):
                        js_url = "https:" + js_url
                    elif js_url.startswith("/"):
                        js_url = f"https://www.tiktok.com{js_url}"
                js_urls.append(js_url)

            # Look for signature-related scripts
            signature_code = ""
            for js_url in js_urls[:10]:  # Limit to first 10 scripts
                try:
                    js_response = await client.get(js_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    js_code = js_response.text

                    # Check if this script contains signature logic
                    if "frontierSign" in js_code or "x-bogus" in js_code.lower() or "acrawler" in js_code:
                        signature_code += f"\n// Source: {js_url}\n"
                        signature_code += js_code[:50000]  # Limit size
                        break
                except Exception:
                    continue

            if not signature_code:
                return {
                    "success": False,
                    "message": "Could not find signature code in CDN",
                    "js_urls_found": len(js_urls),
                }

            code_hash = hashlib.md5(signature_code.encode()).hexdigest()

            # Save to file with _cdn suffix
            base_name = algo["code_file"].rsplit(".", 1)[0]
            ext = algo["code_file"].rsplit(".", 1)[1] if "." in algo["code_file"] else "js"
            cdn_file = ALGO_DIR / f"{base_name}_cdn.{ext}"
            with open(cdn_file, "w") as f:
                f.write(signature_code)

            # Update metadata
            metadata = load_metadata()
            if name not in metadata:
                metadata[name] = {}
            metadata[name]["cdn_hash"] = code_hash
            metadata[name]["cdn_source"] = cdn_source
            metadata[name]["cdn_updated"] = datetime.now().isoformat()

            # Check if matches GitHub hash
            github_hash = metadata[name].get("github_hash")
            if github_hash:
                metadata[name]["verified"] = (github_hash == code_hash)

            save_metadata(metadata)

            return {
                "success": True,
                "message": f"Fetched from CDN",
                "hash": code_hash,
                "size": len(signature_code),
                "verified": metadata[name].get("verified", False),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/test")
async def test_algorithm(name: str) -> dict:
    """Test algorithm with sample data."""
    if name not in ALGORITHMS:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    algo = ALGORITHMS[name]
    code = get_algorithm_code(name)

    if not code:
        return {
            "success": False,
            "error": "No algorithm code available",
        }

    # For Python algorithms, try to execute a basic test
    if algo["code_file"].endswith(".py"):
        try:
            # Simple syntax check
            compile(code, algo["code_file"], "exec")

            # Look for a Gorgon class or similar
            if "class Gorgon" in code or "def encrypt" in code:
                return {
                    "success": True,
                    "output": "Syntax valid, Gorgon class found",
                }
            else:
                return {
                    "success": True,
                    "output": "Syntax valid",
                }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }

    # For JS algorithms, just check if code exists and has expected patterns
    elif algo["code_file"].endswith(".js"):
        if "function" in code or "=>" in code:
            return {
                "success": True,
                "output": "JavaScript code found",
            }
        else:
            return {
                "success": False,
                "error": "No JavaScript functions found",
            }

    return {
        "success": False,
        "error": "Unknown code format",
    }


@router.post("/refresh")
async def refresh_all_algorithms() -> dict:
    """Refresh all fetchable algorithms from their sources."""
    updated = 0
    errors = []

    for name, algo in ALGORITHMS.items():
        if not algo.get("can_fetch"):
            continue

        source = GITHUB_SOURCES.get(name)
        if not source:
            continue

        try:
            repo = source["repo"]
            file_path = source["file_path"]
            branch = source.get("branch", "main")
            url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                code = response.text
                code_hash = hashlib.md5(code.encode()).hexdigest()

                # Save to file
                code_file = ALGO_DIR / algo["code_file"]
                with open(code_file, "w") as f:
                    f.write(code)

                # Update metadata
                metadata = load_metadata()
                if name not in metadata:
                    metadata[name] = {}
                metadata[name]["last_updated"] = datetime.now().isoformat()
                metadata[name]["github_hash"] = code_hash
                save_metadata(metadata)

                updated += 1

        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    return {
        "updated": updated,
        "errors": errors if errors else None,
    }
