# Automation Engine

The Engine tab provides a generic automation framework for any website. Unlike Tasks (which focus on traffic), Engine lets you define complex multi-step workflows with goal detection.

## Overview

The Automation Engine is designed for:
- Login automation
- Form submission
- Multi-step workflows
- Custom scraping tasks
- Any site-specific automation

## How It Works

1. **Navigate**: Browser goes to your target URL
2. **Detect**: Engine analyzes the page structure
3. **Execute**: Runs your defined actions in order
4. **Goal Check**: Stops when goal keywords are found

## Quick Test & Analyze

Before creating a full configuration, analyze any URL:

1. Enter URL in "Quick Test & Analyze"
2. Click **Analyze**
3. Review detected elements:
   - Forms, buttons, inputs
   - Captcha presence
   - Page type (login, dashboard, etc.)
4. Click **Apply Suggestions** to auto-fill config

## Configuration

### Basic Settings

| Field | Description |
|-------|-------------|
| **Target URL** | The starting URL |
| **Site Name** | Friendly name for presets |
| **Goal Keywords** | Stop when these words appear (e.g., "dashboard", "welcome") |

### Captcha Selectors

If the site has captchas:

| Selector | Example |
|----------|---------|
| **Image** | `img.captcha`, `#captcha-image` |
| **Input** | `input#captcha`, `.captcha-input` |
| **Submit** | `button[type=submit]`, `.submit-btn` |

### Actions

Actions are executed in order. Types:

| Action | Usage |
|--------|-------|
| **click** | Click an element: `button.login` |
| **type** | Enter text: `input#email` → `user@example.com` |
| **wait** | Wait for element: `.loading` |
| **scroll** | Scroll to element or position |
| **select** | Choose dropdown option |

#### Adding Actions

1. Click **+ Add Action**
2. Select action type
3. Enter selector (CSS selector)
4. Enter value (for type/select actions)

### Options

| Option | Description |
|--------|-------------|
| **Headless Mode** | Run without visible browser |
| **Solve Captcha** | Auto-solve with OCR |
| **Max Iterations** | Limit action cycles (prevent infinite loops) |

## Preset Templates

Save and reuse configurations:

### Saving a Preset
1. Configure your automation
2. Click **Save Current**
3. Choose category (login, captcha, form, social, custom)

### Loading a Preset
1. Browse preset categories
2. Click a preset card to load
3. Modify if needed

### Built-in Categories

| Category | Use Case |
|----------|----------|
| **Login** | Authentication flows |
| **Captcha** | Sites with captcha challenges |
| **Form** | Form submission workflows |
| **Social** | Social media automation |
| **Custom** | User-saved configurations |

## Example: Login Automation

```
Target URL: https://example.com/login
Goal Keywords: dashboard, welcome, logged in

Actions:
1. type → #email → user@example.com
2. type → #password → secretpassword
3. click → button[type=submit]
```

## Jobs & Monitoring

### Active Jobs
View currently running automations:
- Status (running/completed/failed)
- Current iteration
- Error messages

### Logs
Real-time output showing:
- Navigation events
- Action execution
- Element detection
- Goal matching

### Screenshots
Latest screenshot from the browser session - useful for debugging.

## Best Practices

1. **Analyze First**: Always use Quick Test before configuring
2. **Specific Selectors**: Use IDs when possible (`#email` not `input`)
3. **Goal Keywords**: Choose unique words that only appear on success
4. **Reasonable Iterations**: Set max iterations to prevent runaway loops
5. **Test Headful First**: Debug with visible browser, then switch to headless

## Troubleshooting

### Actions Not Executing
- Verify selectors match current page structure
- Check if elements are inside iframes
- Increase wait times between actions

### Captcha Not Solving
- Ensure Tesseract is installed
- Verify captcha selector is correct
- Some captchas require paid services

### Goal Never Reached
- Check goal keywords for typos
- Verify the flow actually reaches the goal page
- Look for redirect issues

See [Troubleshooting](troubleshooting.md) for more solutions.
