# API Reference

GhostStorm exposes a REST API for programmatic control. All endpoints are prefixed with `/api`.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently no authentication required for local deployment.

## Response Format

All responses are JSON:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

## Tasks API

### Create Task

Create a new automation task.

```http
POST /api/tasks
Content-Type: application/json

{
  "url": "https://example.com",
  "visits": 10,
  "workers": 3,
  "headless": true,
  "use_proxy": true,
  "llm_mode": "off"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Target URL |
| `visits` | integer | Yes | Number of visits |
| `workers` | integer | No | Parallel sessions (default: 1) |
| `headless` | boolean | No | Headless mode (default: true) |
| `use_proxy` | boolean | No | Use proxies (default: false) |
| `llm_mode` | string | No | off/autonomous/assist |
| `vision_mode` | string | No | off/auto/always |

**Response:**
```json
{
  "task_id": "abc123",
  "status": "queued"
}
```

### Get Task

Get task status and results.

```http
GET /api/tasks/{task_id}
```

**Response:**
```json
{
  "task_id": "abc123",
  "status": "running",
  "progress": 5,
  "total": 10,
  "results": [...]
}
```

### List Tasks

Get all tasks.

```http
GET /api/tasks
```

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status |
| `limit` | integer | Max results |
| `offset` | integer | Pagination offset |

### Cancel Task

Stop a running task.

```http
DELETE /api/tasks/{task_id}
```

## Engine API

### Analyze URL

Analyze a URL for automation.

```http
POST /api/engine/analyze
Content-Type: application/json

{
  "url": "https://example.com/login"
}
```

**Response:**
```json
{
  "page_type": "login",
  "elements": {
    "forms": [...],
    "buttons": [...],
    "inputs": [...]
  },
  "captcha_detected": false,
  "suggested_keywords": ["dashboard", "welcome"]
}
```

### Run Automation

Start an engine automation.

```http
POST /api/engine/run
Content-Type: application/json

{
  "url": "https://example.com",
  "name": "My Automation",
  "goal_keywords": ["dashboard", "success"],
  "actions": [
    {"type": "type", "selector": "#email", "value": "test@example.com"},
    {"type": "click", "selector": "button[type=submit]"}
  ],
  "headless": true,
  "solve_captcha": true,
  "max_iterations": 30
}
```

### Get Presets

List saved presets.

```http
GET /api/engine/presets
```

### Save Preset

Save current configuration as preset.

```http
POST /api/engine/presets
Content-Type: application/json

{
  "name": "My Login Preset",
  "category": "login",
  "config": { ... }
}
```

## Proxy API

### Get Stats

Get proxy statistics.

```http
GET /api/proxies/stats
```

**Response:**
```json
{
  "total": 1000,
  "alive": 150,
  "dead": 750,
  "untested": 100
}
```

### Start Scrape

Start scraping proxies from all sources.

```http
POST /api/proxies/scrape
```

### Test Proxies

Test proxies from a file.

```http
POST /api/proxies/test
Content-Type: application/json

{
  "source": "aggregated"
}
```

### Import Proxies

Import proxies from text.

```http
POST /api/proxies/import
Content-Type: application/json

{
  "proxies": "192.168.1.1:8080\n10.0.0.1:3128"
}
```

### Configure Provider

Set up premium proxy provider.

```http
POST /api/proxies/providers/{provider_name}
Content-Type: application/json

{
  "username": "...",
  "password": "...",
  "country": "us",
  "session_type": "rotating"
}
```

## LLM API

### Health Check

Check LLM provider status.

```http
GET /api/llm/health
```

**Response:**
```json
{
  "providers": {
    "ollama": {
      "available": true,
      "models": ["llama3.2-vision"]
    }
  }
}
```

### Get Models

List available models.

```http
GET /api/llm/models
```

## Data API

### Get Categories

List data categories.

```http
GET /api/data/categories
```

### Get Files

List files in a category.

```http
GET /api/data/{category}/files
```

### Generate Data

Generate new data.

```http
POST /api/data/{category}/generate
Content-Type: application/json

{
  "count": 100,
  "browser": "chrome",
  "os": "windows",
  "filename": "generated.txt"
}
```

### Get Items

Get items from a file.

```http
GET /api/data/{category}/{filename}
```

## Zefoy API

### Check Status

Check Zefoy service availability.

```http
GET /api/zefoy/status
```

**Response:**
```json
{
  "services": {
    "views": {"available": true},
    "hearts": {"available": false, "reason": "cooldown"},
    "followers": {"available": true}
  }
}
```

### Start Boost

Start a Zefoy boost job.

```http
POST /api/zefoy/boost
Content-Type: application/json

{
  "video_url": "https://tiktok.com/@user/video/123",
  "services": ["views", "hearts"],
  "repeat": 5,
  "delay": 60,
  "use_proxy": true
}
```

## Settings API

### Get Settings

Get current settings.

```http
GET /api/settings
```

### Update Settings

Update settings.

```http
PUT /api/settings
Content-Type: application/json

{
  "browser": {
    "engine": "patchright",
    "headless": true,
    "workers": 5
  }
}
```

## WebSocket API

### Connect

```
ws://localhost:8000/ws
```

### Events

Events are JSON messages:

```json
{
  "type": "task_progress",
  "task_id": "abc123",
  "progress": 5,
  "total": 10
}
```

**Event Types:**

| Type | Description |
|------|-------------|
| `task_started` | Task began execution |
| `task_progress` | Progress update |
| `task_completed` | Task finished |
| `task_failed` | Task encountered error |
| `log` | Log message |
| `proxy_scraped` | Proxy scrape update |
| `proxy_tested` | Proxy test result |

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request - invalid parameters |
| 404 | Not found - resource doesn't exist |
| 422 | Validation error - check input |
| 500 | Server error - check logs |

## Rate Limits

No rate limits for local deployment. In production, consider implementing:
- Request throttling
- Concurrent task limits
- WebSocket connection limits
