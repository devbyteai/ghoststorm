# Getting Started

This guide walks you through installing and running GhostStorm for the first time.

## Prerequisites

Before installing GhostStorm, ensure you have:

1. **Python 3.10 or higher**
   ```bash
   python --version
   ```

2. **pip (Python package manager)**
   ```bash
   pip --version
   ```

3. **Git** (optional, for cloning)
   ```bash
   git --version
   ```

## Installation

### 1. Clone or Download

```bash
git clone <repository-url>
cd ghoststorm
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Browser

```bash
# Install Patchright browser
patchright install chromium
```

## Running GhostStorm

### Start the Server

```bash
PYTHONPATH=src python -m uvicorn "ghoststorm.api:create_app" --factory --port 8000
```

### Access the Web UI

Open your browser and navigate to:
```
http://localhost:8000
```

## First Steps

### 1. Configure Proxies (Recommended)

1. Go to the **Proxies** tab
2. Click **Scrape All Sources** to gather free proxies
3. Click **Test** to verify which proxies work

### 2. Run Your First Task

1. Go to the **Tasks** tab
2. Enter a URL to visit
3. Set the number of visits
4. Click **Start Task**

### 3. Check Results

- Watch the **Activity Log** for real-time events
- View task status in the task list

## Optional Setup

### Enable AI Control

AI Control requires Ollama with a vision model:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Pull the vision model
ollama pull llama3.2-vision
```

### Enable Captcha Solving

For automatic captcha solving, install Tesseract:

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from https://github.com/tesseract-ocr/tesseract
```

## Directory Structure

```
ghoststorm/
├── src/ghoststorm/        # Source code
│   ├── api/               # Web API and UI
│   ├── core/              # Core automation logic
│   └── services/          # Background services
├── data/                  # Data files (proxies, user agents, etc.)
├── docs/                  # Documentation
└── tests/                 # Test files
```

## Next Steps

- [Tasks Guide](tasks.md) - Learn about mass automation
- [Proxies Guide](proxies.md) - Set up proxy rotation
- [AI Control Guide](ai-control.md) - Use LLM-powered automation
