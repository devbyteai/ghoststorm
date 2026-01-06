# Troubleshooting

Common issues and their solutions for GhostStorm.

## Server Issues

### Server Won't Start

**Symptom:** Error when running `uvicorn`

**Solutions:**
1. Check Python version (need 3.10+):
   ```bash
   python --version
   ```

2. Ensure virtual environment is activated:
   ```bash
   source .venv/bin/activate
   ```

3. Install missing dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Check port availability:
   ```bash
   lsof -i :8000
   ```

### Multiple Servers Running

**Symptom:** Port already in use error

**Solution:**
```bash
# Kill existing servers
pkill -f uvicorn

# Start fresh
PYTHONPATH=src python -m uvicorn "ghoststorm.api:create_app" --factory --port 8000
```

### High Memory Usage

**Solutions:**
- Reduce worker count in Settings
- Enable headless mode
- Clear completed tasks
- Restart server periodically

## Browser Issues

### Browser Won't Launch

**Solutions:**
1. Install browser:
   ```bash
   patchright install chromium
   ```

2. Check permissions:
   ```bash
   chmod +x ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
   ```

3. Install system dependencies (Linux):
   ```bash
   sudo apt install libnss3 libxss1 libasound2
   ```

### Browser Crashes

**Solutions:**
- Reduce workers
- Enable headless mode
- Check available RAM
- Update browser: `patchright install chromium --force`

### Pages Not Loading

**Solutions:**
- Test without proxy first
- Check internet connection
- Increase page timeout
- Verify URL is accessible

## Proxy Issues

### All Proxies Dead

**Solutions:**
1. Scrape fresh proxies
2. Test with smaller batch
3. Try different source types
4. Use premium providers for reliability

### Low Success Rate

**Explanation:** Free proxies typically have 5-15% success rate.

**Solutions:**
- Scrape more proxies
- Test more frequently
- Consider premium providers
- Use faster rotation strategy

### IP Getting Blocked

**Solutions:**
- Enable proxy rotation
- Use more proxies
- Increase delays between requests
- Try residential proxies

## Task Issues

### Tasks Stuck at "Running"

**Solutions:**
1. Check browser processes:
   ```bash
   ps aux | grep chromium
   ```

2. Kill stuck browsers:
   ```bash
   pkill -f chromium
   ```

3. Restart server

### High Failure Rate

**Solutions:**
- Test proxies first
- Increase timeouts
- Check if target blocks automation
- Reduce concurrent workers
- Enable anti-detection features

### Tasks Complete But No Effect

**Solutions:**
- Verify task actually reached target
- Check for captcha blocks
- Review task logs for errors
- Test manually in visible browser

## AI Control Issues

### "Ollama Not Running"

**Solutions:**
1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Start Ollama:
   ```bash
   ollama serve
   ```

3. Pull model:
   ```bash
   ollama pull llama3.2-vision
   ```

4. Verify running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### AI Can't Find Elements

**Solutions:**
- Switch Vision to "Always"
- Be more specific in goals
- Check if element is in iframe
- Try simpler goals first

### Slow AI Response

**Solutions:**
- Use "Auto" or "Off" vision mode
- Consider smaller model
- Check Ollama resource usage
- Reduce screenshot frequency

## Zefoy Issues

### Service Unavailable

**Explanation:** Zefoy services frequently go up and down.

**Solutions:**
- Wait and try later
- Check zefoy.com manually
- Try different services

### Captcha Not Solving

**Solutions:**
1. Install Tesseract:
   ```bash
   sudo apt install tesseract-ocr
   ```

2. Retry (OCR accuracy varies)
3. Consider 2Captcha API for reliability

### No Results on TikTok

**Explanation:** Some boosts take time to appear.

**Solutions:**
- Wait 5-10 minutes
- Check Zefoy submitted successfully
- Verify correct video URL
- Results may not always stick

## Connection Errors

### ERR_CONNECTION_RESET

**Meaning:** Connection was forcibly closed.

**Solutions:**
- Try different proxy
- Check if site is down
- Reduce request rate
- Use residential proxies

### ERR_CONNECTION_REFUSED

**Meaning:** Target refused connection.

**Solutions:**
- Verify URL is correct
- Check if site blocks automation
- Try without proxy
- Check firewall settings

### Timeout Errors

**Solutions:**
- Increase timeout settings
- Use faster proxies
- Check internet connection
- Reduce concurrent workers

## Data Issues

### Generation Fails

**Solutions:**
- Check write permissions
- Ensure data directory exists:
  ```bash
  mkdir -p data/user_agents data/fingerprints
  ```
- Verify disk space

### Data Not Loading

**Solutions:**
- Check file paths
- Verify JSON format
- Restart server
- Check file permissions

## UI Issues

### Page Not Loading

**Solutions:**
- Hard refresh: Ctrl+Shift+R
- Clear browser cache
- Check server is running
- Check console for errors

### WebSocket Disconnected

**Solutions:**
- Refresh page
- Check server status
- Review network connectivity

### Actions Not Responding

**Solutions:**
- Check browser console (F12)
- Refresh page
- Clear browser storage
- Try different browser

## Getting Help

If these solutions don't help:

1. **Check Logs**: Enable debug mode in Settings
2. **Review Console**: Browser dev tools (F12)
3. **Server Logs**: Check terminal output
4. **Restart**: Often fixes temporary issues

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "422 Unprocessable Entity" | Invalid request data | Check input values |
| "500 Internal Server Error" | Server crash | Check logs, restart |
| "Proxy connection failed" | Proxy not working | Test/rotate proxies |
| "Element not found" | Selector doesn't match | Update selectors |
| "Timeout exceeded" | Page too slow | Increase timeout |
| "Browser crashed" | Resource issue | Reduce workers |
