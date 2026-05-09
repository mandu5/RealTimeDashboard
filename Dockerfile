# Mock-mode dashboard image (portfolio / demos). Live capture needs --cap-add=NET_RAW etc.
FROM python:3.11-slim

WORKDIR /app

# scapy imports cleanly; live sniffing in-container still needs extra caps at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcap0.8 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8050

# Render and many PaaS set PORT; default 8050 for local `docker run -p 8050:8050`
CMD ["sh", "-c", "python3 run.py --mode mock --port ${PORT:-8050}"]
