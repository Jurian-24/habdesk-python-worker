import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_url = os.getenv('LARAVEL_API_URL')
headers = {
    "Authorization": f"Bearer {os.getenv('WORKER_TOKEN')}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


try:
    response = requests.get(f"{api_url}/scraper-jobs/next", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        job = data.get('job')
        
        print("\nBackend responds")
        print(f"Message from backend: {data.get('message')}")
        print("-" * 50)

        
        if job:
            experiment = job.get('experiment')
            
            if experiment:
                print(f"EXPERIMENT CODE: {experiment.get('code')}")
                print(f"WORKLOAD:        {experiment.get('workload')}")
                print("\nHISTORISCHE CONTEXT:")
                print(experiment.get('context'))
            else:
                print("No experiment key, check controller")
        else:
            print("No jobs with status queued, check controller")
            
    else:
        print(f"Server error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Something went wrong in the worker: {e}")