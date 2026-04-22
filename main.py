import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('LARAVEL_API_URL')
TOKEN = os.getenv('WORKER_TOKEN')

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

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
                
               # todo: add the scraping logic
                time.sleep(3) 
                
                final_status = "COMPLETED" 
                
                payload = {"status": final_status}
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