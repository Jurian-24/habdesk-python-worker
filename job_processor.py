import os
import time
import requests
import json
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright
import agentql
from llm_providers.gemini_provider import GeminiProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.ollama_provider import OllamaProvider

class JobProcessor:
    def __init__(self):
        load_dotenv()

        self.api_url = os.getenv('LARAVEL_API_URL')
        self.headers = {
        "Authorization": f"Bearer {os.getenv('WORKER_TOKEN')}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        self.llm = OllamaProvider()

    def calculate_confidence(self, schema, results):
        if not schema or not results:
            return 0
        
        total_points = 0
        earned_points = 0
        
        for key, expected_type in schema.items():
            total_points += 2
            

            if key in results and results[key]:
                earned_points += 1
                
                value = results[key]
                expected_type = expected_type.lower()
                
                if expected_type == "array" and isinstance(value, list):
                    earned_points += 1
                elif expected_type == "string" and isinstance(value, str):
                    earned_points += 1
                elif expected_type in ["integer", "decimal", "int", "float"]:
                    try:
                        float(value)
                        earned_points += 1
                    except (ValueError, TypeError):
                        pass
                else:
                    earned_points += 1
                    
        if total_points == 0:
            return 100
            
        return int((earned_points / total_points) * 100)

    def start_worker(self):
        while True:
            job = self.fetch_next_job()

            if job:
                self.process_job(job)
                
                # self.test_setting(job)
            
            time.sleep(10)

    def fetch_next_job(self):
        try:
            response = requests.get(f"{self.api_url}/scraper-jobs/next", headers=self.headers)
            if response.status_code == 200:
                return response.json()['job']
            else:
                print(json.dumps(response.json(), indent=4))

        except requests.exceptions.ConnectionError:
            print("Laravel cannot be reached")
        return None
    
    def process_job(self, job):
        job_id = job['id']

        exp_meta = job.get('experiment', {
            'code': 'UNKNOWN',
            'workload': 'UNKNOWN',
            'context': 'No historical feedback available yet'
        })

        # print(f"Scraper job {job_id} is being processed")
        print(f"Scraper job {job_id} is being processed under Experiment {exp_meta['code']}")

        try:
            start_time = time.time()

            with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
                page = agentql.wrap(browser.new_page())

                try:
                    self.run_job_steps(page, job)

                    # start timing for the response
                    start_time = time.time()
                    
                    end_time = time.time()
                    response_time_ms = int(end_time - start_time * 1000)

                    # start the extraction with agentql
                    extracted_data, token_info = self.extract_data(page, job, exp_meta['context'])

                    schema = job['scraper_job_type']['configuration']['expected_output_format']
                    if isinstance(schema, str):
                        schema = json.loads(schema)

                    confidence_score = self.llm.calculate_confidence(schema, extracted_data)

                    validation_status = "APPROVED" if confidence_score > 70 else "REJECTED"
                    # if confidence_score == 0:
                    #     raise Exception(f"Confidence score is 0. Page probably doesnt exist")
                    self.send_metrics_to_laravel(
                        job_id=job_id,
                        exp_meta=exp_meta,
                        res_time=response_time_ms,
                        tokens=token_info,
                        status=validation_status
                    )
                    self.report_job_status(job_id, "COMPLETED", extracted_data, confidence_score)

                    self.log_experiment_to_laravel(
                        exp_code=exp_meta['code'],
                        workload=exp_meta['workload'],
                        job_id=job_id,
                        res_time=response_time_ms,
                        tokens=token_info,
                        status=validation_status
                    )
                except Exception as inner_e:
                    print(f"Something went wrong while trying to scrape the site: {inner_e}")

                    screenshot_base64 = None

                    resilience = job.get('scraper_job_type', {}).get('resilience_settings', [])

                    if isinstance(resilience, str):
                        resilience = json.loads(resilience)

                    wants_screenshot = any(
                        setting.get('definition', {}).get('key') == 'SCREENSHOT_ON_FAILURE' 
                        and setting.get('active') in [True, 'true', 1, '1']
                        for setting in resilience
                    )

                    if wants_screenshot: 
                        try:
                            screenshot_bytes = page.screenshot(full_page=True)

                            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        except Exception as pic_e:
                            print(f"Not able to make a screenshot of the page: {pic_e}")
                    
                    self.report_job_status(job_id, "FAILED", None, 0, screenshot_base64)

        except Exception as e:
            print(f"Fail outside browser: {job_id}: {e}")
            self.report_job_status(job_id, "FAILED", None, 0)
    
    def run_job_steps(self, page, job):
        """
        Loop through the job steps and navigate. When on the correct page, start scraping
        """
        target_url = job['scraper_job_type']['target_url']
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        time.sleep(2)

        auth_payload_str = job.get('authentication_payload')

        if auth_payload_str:
            auth_payload = json.loads(auth_payload_str)
            username = auth_payload.get('username')
            password = auth_payload.get('password')
            try: 
                print('Checking for the cookie banner')
                try:
                    cookie_elements = page.query_elements("{ accept_cookies_button }")
                    if cookie_elements.accept_cookies_button:
                        cookie_elements.accept_cookies_button.click()
                        page.wait_for_timeout(2000) 
                except Exception as e:
                    print("No cookie banner found. Continueing...")

                login_query = """
                    {
                        username_input
                        password_input
                        login_submit_button
                    }
                """

                print("Fetching the login elements")
                elements = page.query_elements(login_query)
                
                if elements.username_input and elements.password_input:
                    elements.username_input.fill(username)
                    elements.password_input.fill(password)
                    elements.login_submit_button.click()

                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                else:
                    print("AgentQL cannot find the login fields")

            except Exception as e:
                print(f"Logging in has failed: {e}")

    def extract_data(self, page, job, historical_context):
        schema = job['scraper_job_type']['configuration']['expected_output_format']
        prompt = job['scraper_job_type']['configuration']['prompt']
        if isinstance(schema, str):
            schema = json.loads(schema)

        print("komt in extract_data")

        full_prompt = f"""
            HISTORICAL ERROR CONTEXT TO AVOID:
            {historical_context}
            
            ACTUAL EXTRACTION TASK:
            {prompt}
        """

        token_info = {
            'prompt': 1250,
            'completion': 150,
            'total': 1400
        }

        query = self.llm.generate_query(prompt, schema)
        extracted = page.query_data(query)

        return extracted, token_info
    
    def report_job_status(self, job_id, status, results=None, confidence=0, screenshot=None):
        safe_results = results if results is not None else []

        payload = {
            "scraper_job_id": job_id,
            "scraper_job_status": status,
            "scraper_job_results": safe_results,
            "confidence_score": confidence,
            "validation_status": "PENDING",
            'error_screenshot': screenshot
        }

        if screenshot:
            payload["error_screenshot"] = screenshot

        response = requests.patch(f"{self.api_url}/scraper-jobs/{job_id}/status", json=payload, headers=self.headers)

        if response.status_code == 200:
            print(f"Scraper job {job_id} saved with status {status}")
        elif response.status_code == 422:
            print(f"Scraper job {job_id} is missing payload")
            print(json.dumps(response.json(), indent=4))
        else:
            print(f"Scraper job {job_id} could not be saved")

    def log_experiment_to_laravel(self, exp_code, workload, job_id, res_time, tokens, status):
        payload = {
            "experiment_code": exp_code,
            "workload": workload,
            "scraper_job_id": job_id,
            "response_time_ms": res_time,
            "prompt_tokens": tokens['prompt'],
            "completion_tokens": tokens['completion'],
            "total_tokens": tokens['total'],
            "validation_status": status
        }
        try:
            res = requests.post(f"{self.api_url}/experiment-logs", json=payload, headers=self.headers)
            print("\n")
            print(json.dumps(res, indent=4))

            if res.status_code == 201:
                print("Experiment metrics successfully logged to Laravel!")
        except Exception as e:
            print(f"Could not log metrics: {e}")


    def test_setting(self, job):
        screenshot_base64 = None

        resilience = job.get('scraper_job_type', {}).get('resilience_settings', [])

        print(json.dumps(resilience))

        if isinstance(resilience, str):
            resilience = json.loads(resilience)

        wants_screenshot = any(
            setting.get('definition', {}).get('key') == 'SCREENSHOT_ON_FAILURE' 
            and setting.get('active') in [True, 'true', 1, '1']
            for setting in resilience
        )

        if wants_screenshot: 
            try:
                print('maakt screenshot')
                # screenshot_bytes = page.screenshot(full_page=True)

                # screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            except Exception as pic_e:
                print(f"Not able to make a screenshot of the page: {pic_e}")
        
        # self.report_job_status(job_id, "FAILED", None, 0, screenshot_base64)

    def log_experiment_to_laravel(self, job_id, exp_meta, res_time, tokens, status):
        endpoint = f"{self.api_url}/experiment-logs"

        payload = {
            "experiment_code": exp_meta['code'],
            "workload": exp_meta['workload'],
            "scraper_job_id": job_id,
            "response_time_ms": res_time,
            "prompt_tokens": tokens['prompt_tokens'],
            "completion_tokens": tokens['completion_tokens'],
            "total_tokens": tokens['total_tokens'],
            "validation_status": status
        }

        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            if response.status_code == 201:
                print("Metrics stored in the database")
            else:
                print(f"Couldnt save metrics {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Network error while saving: {e}")