import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('LARAVEL_API_URL')
TOKEN = os.getenv('WORKER_TOKEN')

JOB_ID = "01kpr67v3j083yvawrd599xqe8" 

def report_to_laravel():
    print(f"Worker is starting job: {JOB_ID}")

    endpoint = f"{API_URL}/scraper-jobs/{JOB_ID}/status"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "status": "COMPLETED" 
    }

    try:
        response = requests.patch(endpoint, json=payload, headers=headers)

        if response.status_code == 200:
            print(response.json()['message'])
        elif response.status_code == 403:
            print("403")
        elif response.status_code == 422:
            print("422")
            print(response.json())
        else:
            print(f"Error: status Code: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("Laravel not running probably")

if __name__ == "__main__":
    report_to_laravel()