FROM python:3.11-slim

WORKDIR /

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    tesseract-ocr tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install Chromium and all required browser dependencies
RUN playwright install --with-deps chromium

RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

COPY . /app/scraper/

WORKDIR /app

CMD ["celery", "-A", "scraper.celery_app", "worker", "--loglevel=info", "--concurrency=2"]