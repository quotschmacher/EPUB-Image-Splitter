FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \    libxml2 libxslt1.1 libxml2-dev libxslt1-dev gcc \ && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/epub_split_images.py /app/epub_split_images.py
ENTRYPOINT ["python", "/app/epub_split_images.py", "--input", "/in", "--output", "/out"]
