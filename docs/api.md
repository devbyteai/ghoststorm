# API Reference

## REST API

Base URL: `http://localhost:8000/api`

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List all tasks |
| POST | `/tasks` | Create a task |
| GET | `/tasks/{id}` | Get task details |
| DELETE | `/tasks/{id}` | Delete a task |
| POST | `/tasks/{id}/retry` | Retry a task |

### Flows

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/flows` | List all flows |
| POST | `/flows` | Create a flow |
| GET | `/flows/{id}` | Get flow details |
| POST | `/flows/{id}/execute` | Execute a flow |
| POST | `/flows/record/start` | Start recording |
| POST | `/flows/record/stop` | Stop recording |

### Proxies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/proxies` | List proxies |
| POST | `/proxies/scrape` | Scrape proxies |
| POST | `/proxies/test` | Test proxies |

### LLM

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/llm/providers` | List providers |
| POST | `/llm/complete` | Get completion |
| GET | `/llm/models` | List models |

## WebSocket API

Connect to `ws://localhost:8000/ws`

### Events

| Event | Description |
|-------|-------------|
| `task:created` | New task created |
| `task:started` | Task execution started |
| `task:progress` | Task progress update |
| `task:completed` | Task completed |
| `task:failed` | Task failed |

### Message Format

```json
{
  "type": "task:progress",
  "data": {
    "task_id": "uuid",
    "progress": 50,
    "message": "Processing..."
  }
}
```
