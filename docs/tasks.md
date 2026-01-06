# Tasks

The Tasks tab is the main control center for mass browser automation. Use it to send traffic, run batch operations, or automate interactions across multiple URLs.

## Overview

Tasks allow you to:
- Visit URLs with multiple browser sessions
- Simulate human-like browsing behavior
- Use proxies for IP rotation
- Execute custom actions on pages
- Run LLM-powered automation

## Creating a Task

### Basic Task

1. **URL**: Enter the target URL (e.g., `https://example.com`)
2. **Visits**: Number of times to visit the URL
3. **Workers**: Parallel browser sessions (more = faster but more resource-intensive)

### Task Options

| Option | Description |
|--------|-------------|
| **Headless** | Run browsers without visible window |
| **Use Proxy** | Route traffic through proxies |
| **Rotate Proxy** | Use different proxy for each visit |
| **Vision (LLM)** | Enable AI vision for intelligent automation |

## Task Modes

### Standard Mode
Basic URL visiting with optional behavior simulation:
- Page load
- Scroll simulation
- Random delays
- Link clicking (if configured)

### LLM Mode
AI-powered automation that can:
- Understand page content
- Find and interact with elements
- Fill forms intelligently
- Navigate complex flows

Enable LLM mode by toggling "Vision (LLM)" in task options.

## Task Status

| Status | Meaning |
|--------|---------|
| **Queued** | Task waiting to start |
| **Running** | Task in progress |
| **Completed** | Task finished successfully |
| **Failed** | Task encountered errors |
| **Paused** | Task temporarily stopped |

## Monitoring Tasks

### Activity Log
Real-time feed showing:
- Task start/completion
- Individual visit results
- Errors and warnings
- Proxy usage

### Task Statistics
- Total runs
- Success rate
- Average duration
- Errors encountered

## Advanced Usage

### Batch URLs
Process multiple URLs by entering them one per line:
```
https://example.com/page1
https://example.com/page2
https://example.com/page3
```

### Custom Behaviors
Configure behaviors in the **Data** tab:
- Scroll patterns
- Click behaviors
- Time on page
- Mouse movements

### Proxy Configuration
For best results:
1. Scrape proxies in the **Proxies** tab
2. Test them to filter dead ones
3. Enable "Use Proxy" in task options

## Best Practices

1. **Start Small**: Begin with 1-5 workers to test
2. **Use Proxies**: Avoid IP bans with rotation
3. **Add Delays**: Natural timing looks more human
4. **Monitor Logs**: Watch for errors and adjust
5. **Headless Mode**: Use headless for production runs

## Troubleshooting

### Task Stuck at "Running"
- Check if browser processes are frozen
- Restart the server
- Reduce worker count

### High Failure Rate
- Test your proxies
- Increase timeouts
- Check if target site is blocking

### Memory Issues
- Reduce worker count
- Enable headless mode
- Restart periodically

See [Troubleshooting](troubleshooting.md) for more solutions.
