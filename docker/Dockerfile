FROM python:3.11-slim

# Nur die Pakete, die zuverlässig auf Trixie vorhanden sind.
# (libxslt1.1 bitte NICHT installieren – existiert hier nicht.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxml2-dev libxslt1-dev build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/epub_split_images.py /app/epub_split_images.py

# Standardlauf: /in -> /out
ENTRYPOINT ["python", "/app/epub_split_images.py", "--input", "/in", "--output", "/out"]
