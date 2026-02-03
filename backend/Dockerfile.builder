FROM python:3.11-slim

# Builder is primarily for x86 (training/export), but we add arch fallback for flexibility
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps - some may not be available on all platforms
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libglib2.0-0 \
        libgl1 \
        libxcb1 \
        libxext6 \
        libxrender1 \
    && apt-get install -y --no-install-recommends libheif1 || true \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt || \
    (grep -v pillow-heif /app/requirements.txt > /tmp/req.txt && \
     pip install --no-cache-dir -r /tmp/req.txt)

# Ultralytics for bootstrap/export (may not install on all archs)
RUN pip install --no-cache-dir ultralytics || \
    echo "Warning: ultralytics not available on $TARGETARCH - model export disabled"

COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
