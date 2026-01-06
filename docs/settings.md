# Settings

The Settings tab configures global application preferences for browser behavior, proxy handling, API keys, and advanced options.

## Browser Settings

### Default Browser Engine

Choose the automation engine:

| Engine | Description |
|--------|-------------|
| **Patchright** | Enhanced Playwright with anti-detection (Recommended) |
| **Playwright** | Standard Playwright automation |
| **Camoufox** | Firefox-based stealth browser |

### Headless Mode

Run browsers without visible window:
- **Enabled**: Faster, less resource use, no GUI needed
- **Disabled**: See browser actions, useful for debugging

### Default Workers

Number of parallel browser sessions:
- **Minimum**: 1
- **Recommended**: 5-10
- **Maximum**: 50 (depends on system resources)

**Resource Impact:**
- Each worker = ~200-500MB RAM
- 5 workers ≈ 1-2.5GB RAM
- Adjust based on available memory

## Proxy Settings

### Proxy Rotation Strategy

How to select proxies:

| Strategy | Behavior |
|----------|----------|
| **Weighted** | Prefer proxies with higher success rate |
| **Round Robin** | Cycle through proxies in order |
| **Random** | Pick random proxy each time |
| **Least Used** | Prefer less-used proxies |
| **Fastest** | Prefer proxies with lowest latency |
| **Sticky** | Keep same proxy for session |

**Recommendations:**
- General use: Weighted
- Even distribution: Round Robin
- Avoiding patterns: Random
- Session consistency: Sticky

### Auto-test Proxies

Automatically test proxies before using:
- **Enabled**: Skip dead proxies, slower startup
- **Disabled**: Use proxies as-is, faster startup

### Proxy Timeout

Maximum wait time for proxy connection:
- **Range**: 1-60 seconds
- **Default**: 10 seconds
- **Slow proxies**: Increase to 15-30
- **Fast proxies**: Can reduce to 5

## API Keys

### 2Captcha API Key

For external captcha solving service:
1. Register at 2captcha.com
2. Get API key from dashboard
3. Paste key here
4. Used when OCR fails

### Decodo API Key

For Decodo proxy service:
1. Register at decodo.com
2. Get API credentials
3. Paste key here
4. Configure in Proxies tab

### BrightData API Key

For BrightData proxy service:
1. Register at brightdata.com
2. Get API credentials
3. Paste key here
4. Configure zones in Proxies tab

## Advanced Settings

### Debug Mode

Enable verbose logging:
- **Enabled**: Detailed logs, helpful for troubleshooting
- **Disabled**: Standard logging, less console noise

Debug mode logs:
- HTTP requests/responses
- Browser actions
- Proxy selections
- Error stack traces

### Auto-save Config

Save settings automatically:
- **Enabled**: Changes saved immediately
- **Disabled**: Must click Save manually

## Saving Settings

### Save Settings
Click to persist current configuration.

### Reset to Defaults
Restore all settings to original values.

## Configuration File

Settings are stored in `config/settings.json`:

```json
{
  "browser": {
    "engine": "patchright",
    "headless": true,
    "workers": 5
  },
  "proxy": {
    "strategy": "weighted",
    "auto_test": true,
    "timeout": 10
  },
  "api_keys": {
    "2captcha": "...",
    "decodo": "...",
    "brightdata": "..."
  },
  "advanced": {
    "debug": false,
    "autosave": true
  }
}
```

## Environment Variables

Override settings via environment:

| Variable | Setting |
|----------|---------|
| `GHOSTSTORM_HEADLESS` | Headless mode |
| `GHOSTSTORM_WORKERS` | Worker count |
| `GHOSTSTORM_DEBUG` | Debug mode |
| `CAPTCHA_API_KEY` | 2Captcha key |

## Best Practices

### For Production
- Enable headless mode
- Use weighted proxy strategy
- Enable auto-test
- Disable debug mode
- Set appropriate workers for your system

### For Development
- Disable headless mode
- Enable debug mode
- Use fewer workers
- Higher proxy timeout

### For Low Resources
- Reduce workers to 1-3
- Enable headless mode
- Increase proxy timeout
- Disable auto-test

## Troubleshooting

### Settings Not Saving
- Check file permissions
- Ensure config directory exists
- Try manual save button

### Workers Crashing
- Reduce worker count
- Check system memory
- Enable headless mode

### Slow Performance
- Reduce workers
- Lower proxy timeout
- Disable debug mode
- Use faster proxy strategy

### API Keys Not Working
- Verify key is correct
- Check account status
- Ensure service is active

See [Troubleshooting](troubleshooting.md) for more solutions.
