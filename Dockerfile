FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY lobbyharvest/pyproject.toml lobbyharvest/uv.lock ./lobbyharvest/

# Install Python dependencies
RUN pip install uv && \
    cd lobbyharvest && \
    uv sync && \
    uv run playwright install chromium

# Set up Xvfb
ENV DISPLAY=:99
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 &\nexec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]