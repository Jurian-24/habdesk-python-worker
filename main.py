import os
import time
import json
import string
import random
import requests
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('LARAVEL_API_URL')
TOKEN = os.getenv('WORKER_TOKEN')

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def mock_string():
    return ''.join(random.choices(string.ascii_letters, k=8))

def mock_integer():
    return random.randint(1, 1000)

def mock_array():
    return [mock_string(), mock_string(), mock_string()]

generator_map = {
    'string': mock_string,
    'integer': mock_integer,
    'int': mock_integer,
    'array': mock_array
}

def process_job(job):
    expected_format = json.loads(job['scraper_job_type']['configuration']['expected_output_format'])
    mock_data = {}

    for key, expected_type in expected_format.items():
        generate_function = generator_map.get(expected_type.lower(), mock_string)
        
        mock_data[key] = generate_function()

    return mock_data

def poll_for_jobs():
    print("Looking for jobs with status QUEUED \n")
    
    while True:
        try:
            response = requests.get(f"{API_URL}/scraper-jobs/next", headers=HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                job = data['job']
                job_id = job['id']
                
                print(f"{job_id} status -> PROCESSING")
                
                job_results = process_job(job)
                
                final_status = "COMPLETED" 
                
                payload = {
                    "scraper_job_status": final_status,
                    "scraper_job_results": job_results,
                    "confidence_score": 90,

                    'scraper_job_id': job_id,
                    'validation_status': 'PENDING'
                }
                
                update_res = requests.patch(f"{API_URL}/scraper-jobs/{job_id}/status", json=payload, headers=HEADERS)
                
                if update_res.status_code == 200:
                    print(f"{job_id} status -> {final_status}.\n")
                else:
                    print(f"{update_res.text}")
                
            elif response.status_code == 404:
                pass
                
            elif response.status_code == 403:
                print("No rights to update the status of a job 403")
                
            else:
                print(f"{response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("Cannot reach Laravel")
            
        time.sleep(5) 

if __name__ == "__main__":
    poll_for_jobs()