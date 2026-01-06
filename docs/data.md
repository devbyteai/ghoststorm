# Data Management

The Data tab manages all the data files used for browser fingerprinting and anti-detection: user agents, fingerprints, referrers, screen sizes, and more.

## Overview

To avoid detection, automation needs to look human. This requires:
- Varied browser signatures
- Realistic fingerprints
- Natural traffic sources
- Human-like behaviors

## Data Categories

### User Agents

Browser identification strings sent with every request.

**Example:**
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

**Options:**
- **Generate**: Create new user agents for specific browser/OS
- **Manage**: View, add, delete entries

**Generation Settings:**
- Browser: Chrome, Firefox, Safari, Edge
- OS: Windows, macOS, Linux, Android, iOS

### Fingerprints

Complete browser profiles including:
- Screen resolution
- Installed plugins
- WebGL renderer
- Canvas fingerprint
- Audio context
- Timezone

**Options:**
- **Generate**: Create realistic fingerprints
- **Manage**: View and edit fingerprint profiles

### Referrers

Traffic source URLs to simulate organic visitors.

**Common referrers:**
```
https://www.google.com/search?q=...
https://www.facebook.com/
https://twitter.com/
https://t.co/...
```

**Options:**
- **Generate**: Create varied referrer URLs
- **Manage**: Add custom referrers

### Screen Sizes

Resolution profiles matching real devices.

**Common sizes:**
```
1920x1080 (Full HD)
1366x768 (Laptop)
2560x1440 (QHD)
390x844 (iPhone)
```

**Options:**
- **Generate**: Create varied resolutions
- **Manage**: Add custom sizes

### Blacklists

URLs and domains to avoid:
- Ad networks
- Analytics services
- Tracking pixels

### Behavior Patterns

Human-like interaction patterns:
- Scroll speeds
- Mouse movements
- Click patterns
- Time on page

### Evasion Scripts

Anti-detection JavaScript:
- WebGL spoofing
- Canvas fingerprint masking
- Plugin hiding
- Timezone simulation

## Generating Data

### Generate Modal

1. Click **Generate** on any category
2. Configure:
   - **Count**: How many to generate (10-500)
   - **Browser**: Target browser (for UA/fingerprints)
   - **OS**: Target operating system
   - **Filename**: Where to save
3. Click **Generate & Save**

### Example: Generate User Agents

```
Category: User Agents
Count: 100
Browser: Chrome
OS: Windows
Filename: chrome_windows_ua.txt
```

## Managing Data

### Data Manager

1. Click **Manage** on any category
2. Select file from dropdown
3. Browse existing items
4. Search/filter as needed
5. Add or delete items

### Adding Items

1. Open Data Manager
2. Enter new item in text field
3. Click **Add**

### Deleting Items

1. Find item in list
2. Click delete icon
3. Confirm deletion

## Data Files

Data is stored in the `data/` directory:

| Directory | Contents |
|-----------|----------|
| `user_agents/` | Browser UA strings |
| `fingerprints/` | JSON fingerprint profiles |
| `referrers/` | Traffic source URLs |
| `screen_sizes/` | Resolution data |
| `blacklists/` | Blocked domains |
| `behavior/` | Interaction patterns |
| `evasion/` | Anti-detect scripts |

## Integration

### With Tasks
- User agents rotate per request
- Fingerprints applied to browser
- Referrers set on navigation

### With Engine
- Full fingerprint spoofing
- Evasion scripts injected
- Behaviors simulated

## Best Practices

### User Agents
- Keep 100+ varied UAs
- Match UA to task (desktop vs mobile)
- Update monthly for new versions

### Fingerprints
- Generate for target browser
- Include varied screen sizes
- Mix of hardware profiles

### Referrers
- Use realistic sources
- Match to task type
- Include direct traffic

### Behaviors
- Vary scroll patterns
- Randomize click timings
- Include idle periods

## Troubleshooting

### Generation Fails
- Check write permissions
- Ensure data directory exists
- Verify disk space

### Detection Despite Data
- Use more variety
- Check for consistency issues
- Enable evasion scripts

### Performance Issues
- Reduce fingerprint complexity
- Use fewer evasion scripts
- Simplify behaviors

See [Troubleshooting](troubleshooting.md) for more solutions.
