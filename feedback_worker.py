import os
import time
import requests
import json
from dotenv import load_dotenv
from feedback_processor import FeedbackProcessor

from llm_providers.openai_provider import OpenAIProvider

class FeedbackWorker:
    def __init__(self):
        load_dotenv()
        self.api_url = os.getenv('LARAVEL_API_URL')
        self.headers = {
            "Authorization": f"Bearer {os.getenv('WORKER_TOKEN')}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.optimizer = OpenAIProvider()

    def start_polling(self):
        print("Waiting for feedback")
        
        while True:
            jobs_to_process = self.fetch_rejected_jobs()
            
            if jobs_to_process:
                self.process_in_bulk(jobs_to_process)
                time.sleep(10)
            else:
                time.sleep(10) 

    def fetch_rejected_jobs(self):
        try:
            response = requests.get(f"{self.api_url}/validation-feedback/pending", headers=self.headers)
            if response.status_code == 200:
                return response.json().get('data', [])
        except requests.exceptions.ConnectionError:
            print("Laravel onbereikbaar...")
        return []

    def process_in_bulk(self, jobs):
        successful_updates = []

        try:
            for job in jobs:
                print(f"Starting job with type {job['scraper_job_type_id']}")
                job_type_id = job['scraper_job_type_id']
                feedback_id = job['feedback_id']
                
                old_prompt = job['old_prompt']
                human_feedback = job['reason']
                
                if job['results_validation_status'] == 'HUMAN_APPROVED':
                    print("This job is good. No need to improve the prompt")
                    continue

                new_prompt = self.optimizer.create_better_prompt(old_prompt, human_feedback)
                
                if new_prompt:
                    successful_updates.append({
                        "scraper_job_type_id": job_type_id,
                        "feedback_id": feedback_id,
                        "new_prompt": new_prompt
                    })

                    payload = {
                        "scraper_job_type_id": job_type_id,
                        "feedback_id": feedback_id,
                        "new_prompt": new_prompt
                    }

                    self.send_prompt_to_laravel(payload)
                else:
                    print("Gemini couldnt write a prompt")

        except Exception as e:
            print(e)

        # finally:
        #     if successful_updates:
        #         self.send_bulk_to_laravel(successful_updates)
        #     else:
        #         print("Geen succesvolle updates om te versturen.")

    def send_bulk_to_laravel(self, batch_payload):
        try:
            response = requests.patch(
                f"{self.api_url}/validation-feedback/prompt/update", 
                json={"updates": batch_payload},
                headers=self.headers
            )
            
            if response.status_code != 200:
                print(f"Laravel coldnt process the bulk: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Couldnt send the bulk update: {e}")

    def send_prompt_to_laravel(self, payload):
        endpoint_url = f"{self.api_url}/validation-feedback/prompt/update"

        try:
            response = requests.patch(
                endpoint_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                print("Single prompt has been updated")
                return True
            
            elif response.status_code == 422:
                print("Validation error")
                print(json.dumps(response.json(), indent=4))
                return False
                
            else:
                print(f"Could not update the prompt (Status: {response.status_code}).")
                print(f"Error details: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            print("🚨 FATAL: Kan Laravel niet bereiken. Staat Laravel Sail wel aan?")
            return False
        except Exception as e:
            print(e)
            return False
        
if __name__ == "__main__":
    worker = FeedbackWorker()
    worker.start_polling()