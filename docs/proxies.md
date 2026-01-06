# Proxy Management

The Proxies tab handles all proxy-related operations: scraping from free sources, testing, rotation, and premium provider configuration.

## Overview

Proxies are essential for:
- Avoiding IP bans
- Geographic targeting
- Rate limit distribution
- Anonymity

## Proxy Statistics

| Stat | Description |
|------|-------------|
| **Total** | All proxies in the system |
| **Alive** | Working proxies (tested) |
| **Dead** | Non-working proxies |
| **Untested** | Scraped but not verified |

## Scraping Free Proxies

### Scrape All Sources
Click **Scrape All Sources** to fetch from 50+ free proxy lists:

- ProxyNova
- Spys.one
- HideMy.name
- Geonode
- And many more...

Progress modal shows:
- Current source
- Proxies found
- Testing progress
- Alive count

### Source Types

| Type | Description |
|------|-------------|
| **API/Text Lists** | Plain text proxy lists |
| **HTML Tables** | Web pages with proxy tables |
| **ProxyNova** | ProxyNova.com scraper |
| **HideMy** | HideMy.name scraper |
| **Spys** | Spys.one with JS decoding |
| **Geonode** | Geonode API |

## Testing Proxies

### Test All
Click **Test** to verify proxies work:

1. Select source file:
   - **aggregated.txt**: All scraped proxies
   - **alive_proxies.txt**: Previously verified proxies

2. Watch progress:
   - Tested count
   - Alive/dead split
   - ETA

3. Results saved to `alive_proxies.txt`

### Clear Dead
Remove non-working proxies:

1. Click **Clear Dead**
2. Select source file
3. Confirm

## Importing Proxies

### Manual Import
Paste proxies directly:
```
192.168.1.1:8080
103.152.112.24:80
proxy.example.com:3128
```

Format: `ip:port` or `host:port`

### File Upload
Upload a `.txt` or `.csv` file with proxies.

## Adding Custom Sources

Add your own proxy sources:

1. Enter source name
2. Enter URL (must return plain text list)
3. Click **Add Source**

## Premium Providers

Configure paid rotating proxies for better reliability:

### Supported Providers

| Provider | Features |
|----------|----------|
| **Decodo** | $3.50/GB, residential |
| **Bright Data** | Enterprise, multiple zones |
| **Oxylabs** | $8/GB, datacenter & residential |
| **IPRoyal** | $5.50/GB, rotating |
| **Webshare** | Free tier available |

### Configuration

1. Click **Configure** on a provider
2. Enter credentials:
   - Username/Password
   - API Key (some providers)
   - Customer ID (Bright Data)
3. Select options:
   - Country targeting
   - City (optional)
   - Session type (rotating/sticky)
4. Click **Test Connection**
5. Click **Save Provider**

### Session Types

| Type | Behavior |
|------|----------|
| **Rotating** | New IP each request |
| **Sticky** | Same IP for session duration |

## Source Filtering

### Search
Type in search box to filter sources by name.

### Filter by Type
Select source type from dropdown:
- All Types
- API/Text Lists
- HTML Tables
- Specific scrapers

## Proxy Files

| File | Contents |
|------|----------|
| `aggregated.txt` | All scraped proxies |
| `alive_proxies.txt` | Tested working proxies |
| `dead_proxies.txt` | Failed proxies |
| `premium_config.json` | Provider credentials |

## Best Practices

### For Free Proxies
1. Scrape fresh proxies regularly
2. Always test before using
3. Clear dead proxies to save space
4. Use rotation to distribute load

### For Premium Providers
1. Start with rotating session
2. Use geo-targeting when needed
3. Monitor usage to control costs
4. Test connection before tasks

### General Tips
- More alive proxies = better distribution
- Rotate by request, not time
- Monitor success rates
- Clear dead proxies weekly

## Troubleshooting

### Scraping Stuck
- Some sources may timeout
- Click minimize and let it continue
- Try again if sources fail

### Low Alive Rate
- Normal for free proxies (5-15% typical)
- Premium providers have ~99% success

### Provider Test Fails
- Verify credentials
- Check account status
- Ensure funds available

### Proxies Getting Blocked
- Rotate more frequently
- Try different geographic targets
- Use residential over datacenter

See [Troubleshooting](troubleshooting.md) for more solutions.
