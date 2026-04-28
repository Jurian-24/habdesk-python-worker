import os
import time
import requests
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright
import agentql

class JobProcessor:
    def __init__(self):
        load_dotenv()

        self.api_url = os.getenv('LARAVEL_API_URL')
        self.headers = {
        "Authorization": f"Bearer {os.getenv('WORKER_TOKEN')}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

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
            
            time.sleep(10)

    def fetch_next_job(self):
        try:
            response = requests.get(f"{self.api_url}/scraper-jobs/next", headers=self.headers)
            if response.status_code == 200:
                return response.json()['job']
            else:
                print(response)
        except requests.exceptions.ConnectionError:
            print("Laravel cannot be reached")
        return None
    
    def process_job(self, job):
        job_id = job['id']

        print(f"Scraper job {job_id} is being processed")

        try:
            with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
                page = agentql.wrap(browser.new_page())
                
                self.run_job_steps(page, job)
                
                extracted_data = self.extract_data(page, job)

                schema = job['scraper_job_type']['configuration']['expected_output_format']
                if isinstance(schema, str):
                    schema = json.loads(schema)

                confidence_score = self.calculate_confidence(schema, extracted_data)

                self.report_job_status(job_id, "COMPLETED", extracted_data, confidence_score)

        except Exception as e:
            print(f"{job_id}: {e}")
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

            if username and password:
                try:
                    try:
                        print('Checking for cookie header')
                        page.get_by_prompt("Accept cookies button").click()
                        time.sleep(1)
                    except:
                        pass

                    page.get_by_prompt("Username, email or phonenumber input field").fill(username)
                    page.get_by_prompt("Password input field").fill(password)

                    page.get_by_prompt("Log in, sign in, or submit button").click()

                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                except Exception as e:
                    print(f"Logging in has failed: {e}")

    # def generate_query(self, schema):
    #     query_lines = ["{"]
        
    #     for key, data_type in schema.items():
    #         query_lines.append(f"    {key}[]" if data_type.lower() == "array" else f"    {key}")
    #     query_lines.append("}")

    #     dynamic_query = "\n".join(query_lines)

    #     return dynamic_query

    def extract_data(self, page, job):
        schema = job['scraper_job_type']['configuration']['expected_output_format']
        prompt = job['scraper_job_type']['configuration']['prompt']
        if isinstance(schema, str):
            schema = json.loads(schema)

        query = self.create_agentql_query_by_gemini(prompt)

        return page.query_data(query)
    
    def report_job_status(self, job_id, status, results=None, confidence=0):
        safe_results = results if results is not None else {}

        payload = {
            "scraper_job_id": job_id,
            "scraper_job_status": status,
            "scraper_job_results": safe_results,
            "confidence_score": confidence,
            "validation_status": "PENDING"
        }

        response = requests.patch(f"{self.api_url}/scraper-jobs/{job_id}/status", json=payload, headers=self.headers)

        if response.status_code == 200:
            print(f"Scraper job {job_id} saved with status {status}")
        elif response.status_code == 422:
            print(f"Scraper job {job_id} is missing payload")
        else:
            print(f"Scraper job {job_id} could not be saved")

    def create_agentql_query_by_gemini(self, prompt): 
        client = genai.Client()
    
        instructions = """
            You are an expert at writing AgentQL queries for web scraping. 
            AgentQL uses a GraphQL-like syntax to extract UI elements from a webpage. 
            
            CRITICAL RULES:
            - NEVER use SQL syntax (no SELECT, GROUP BY, FROM, etc.).
            - Use standard AgentQL dict/list syntax based on the visual layout of a page.
            
            Example of valid AgentQL syntax:
            {
                monthly_usage {
                    month_name
                    days[] {
                        day_number
                        usage_mb
                    }
                }
            }
            
            Respond ONLY with the raw AgentQL query block based on the user's intent. Do not include markdown code blocks (like ```graphql), formatting, or explanations.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Write an AgentQL query to extract: {prompt}",
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                temperature=0.1
            )
        )
        
        return response.text