FROM python:3.12-slim

# System deps for browser engines (Chromium/Firefox)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # X11 and display
    libx11-6 libxdamage1 libxext6 libxfixes3 libxkbcommon0 \
    libxcomposite1 libxrandr2 libxcursor1 libxi6 \
    # GTK and rendering
    libatk1.0-0 libatk-bridge2.0-0 libpango-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 \
    # Security and crypto
    libssl3 libnss3 libnspr4 \
    # Graphics and GPU
    libegl1-mesa libgbm1 libdrm2 \
    # Audio and fonts
    libasound2 fonts-liberation \
    # Utils
    curl dbus \
    && rm -rf /var/lib/apt/lists/*

# Start dbus (needed for some browser features)
RUN mkdir -p /run/dbus

WORKDIR /app

# Install Python deps first (better caching)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e . && \
    rm -rf /root/.cache

# Copy app code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Browser install script + entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment for browser paths
ENV PLAYWRIGHT_BROWSERS_PATH=/browsers
ENV PATCHRIGHT_BROWSERS_PATH=/browsers
ENV CAMOUFOX_BROWSER_PATH=/browsers/camoufox

# Disable sandbox for container environment
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PATCHRIGHT_SKIP_BROWSER_DOWNLOAD=1

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ghoststorm", "serve", "--host", "0.0.0.0", "--port", "8080"]
