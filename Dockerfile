FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install \
    "python-dotenv>=1.2.2,<2.0.0" \
    "requests>=2.33.1,<3.0.0" \
    "google-genai>=1.73.1,<2.0.0" \
    "playwright" \
    "agentql" \
    "openai"

RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]