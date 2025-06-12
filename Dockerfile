FROM node:18-slim

RUN apt-get update && \
    apt-get install -y python3 python3-venv python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY http_wrapper.py .

RUN mkdir -p /opt/mcp-data && chmod 777 /opt/mcp-data

ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "http_wrapper.py"]
