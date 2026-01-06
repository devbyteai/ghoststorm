# AI Control

The AI Control tab enables LLM-powered browser automation. Instead of defining explicit selectors and actions, describe your goal in natural language and let the AI figure out how to achieve it.

## Prerequisites

AI Control requires Ollama with a vision model:

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama service
ollama serve

# 3. Pull the vision model
ollama pull llama3.2-vision
```

**Note**: The AI Control page will show a warning if Ollama is not running.

## How It Works

1. **Screenshot**: Browser captures the current page
2. **Analysis**: LLM analyzes the visual and DOM content
3. **Action**: AI determines the best action to achieve your goal
4. **Execute**: Action is performed in the browser
5. **Repeat**: Process continues until goal is reached

## Configuration

### Provider & Model

| Setting | Options |
|---------|---------|
| **Provider** | Ollama (Local) |
| **Model** | Llama 3.2 Vision (Recommended) |

### Control Mode

| Mode | Behavior |
|------|----------|
| **Autonomous** | AI executes actions automatically |
| **Assist** | AI suggests actions, you approve each one |

### Vision Settings

| Setting | Description |
|---------|-------------|
| **Auto** | Uses DOM first, falls back to screenshot |
| **Always** | Always sends screenshots to LLM |
| **Off** | DOM text only (faster, less accurate) |

## Creating an AI Task

### 1. Set Target URL
Enter the starting URL:
```
https://example.com
```

### 2. Describe Your Goal
Use natural language:
```
Find the login button and fill in the form with test@example.com and password123
```

Good goals are:
- **Specific**: "Click the blue Sign Up button" not "Sign up"
- **Sequential**: "First accept cookies, then click login"
- **Observable**: Goals the AI can verify visually

### 3. Start Task
Click **Start AI Task** to begin.

## Live View

The center panel shows:
- **Live Screenshot**: Current browser view
- **URL Bar**: Current page URL
- **Element Highlight**: Shows where AI is focusing

## AI Analysis Panel

Shows the AI's understanding:
- **Confidence**: How certain the AI is
- **Analysis**: What the AI sees and thinks
- **Suggested Action**: Next action to take

### Action Types

| Action | Example |
|--------|---------|
| **click** | Click "Login" button |
| **type** | Enter "user@example.com" in email field |
| **scroll** | Scroll down to see more content |
| **wait** | Wait for page to load |
| **navigate** | Go to a different URL |

## Assist Mode

In Assist mode, you control each action:

1. AI analyzes the page
2. AI suggests an action
3. Review the suggestion
4. Click **Approve** or **Reject**
5. AI proceeds based on your choice

Use Assist mode when:
- Testing a new workflow
- Handling sensitive operations
- Debugging AI behavior

## Detected Elements

Right panel shows interactive elements:
- Buttons
- Links
- Inputs
- Forms
- Images

Click any element to highlight it on the live view.

## Action Timeline

History of all actions taken:
- Timestamps
- Action types
- Success/failure status
- Screenshots at each step

## Usage & Costs

| Metric | Value |
|--------|-------|
| **Tokens** | Shows LLM token consumption |
| **Cost** | Free (Local Ollama) |

## Best Practices

### Writing Good Goals

**Good**:
```
Navigate to the contact page, fill in the name field with "John Doe", email with "john@example.com", and submit the form
```

**Bad**:
```
Fill form
```

### Tips

1. **Be Specific**: Include button colors, positions, or text
2. **Break Down Complex Tasks**: Multi-step goals work better than vague ones
3. **Use Assist First**: Test with manual approval before autonomous
4. **Check Vision Mode**: Use "Always" for visually complex sites
5. **Monitor Tokens**: Vision mode uses more tokens

## Troubleshooting

### "Ollama Not Running"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### AI Can't Find Elements
- Switch Vision to "Always"
- Be more specific in your goal
- Check if element is in an iframe

### Actions Failing
- Increase delays in settings
- Check if page has anti-bot protection
- Try with proxy enabled

### Slow Performance
- Use "Auto" or "Off" vision mode
- Consider a faster model
- Reduce screenshot frequency

See [Troubleshooting](troubleshooting.md) for more solutions.
