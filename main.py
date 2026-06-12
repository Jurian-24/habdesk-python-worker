import os
import requests
from job_processor import JobProcessor
from dotenv import load_dotenv
import json
import re

from llm_providers.ollama_provider import OllamaProvider

load_dotenv()

def set_worker_token():
    token = os.getenv("WORKER_TOKEN")

    if not token:
        payload = {
            "email": os.getenv('WORKER_EMAIL'),
            "password": os.getenv('WORKER_PASSWORD')
        }
        url = os.getenv('LARAVEL_API_URL')

        response = requests.post(f"{url}/tokens/worker/create", json=payload)

        data = response.json()
        os.environ["WORKER_TOKEN"] = data['token']

    return os.getenv("WORKER_TOKEN") is not None

if __name__ == "__main__":
    set_worker_token()
    
    worker = JobProcessor()
    worker.start_worker()
