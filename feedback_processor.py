import json
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

class FeedbackProcessor:
    def __init__(self):
        load_dotenv()
        self.client = genai.Client()

    def create_better_prompt(self, old_prompt: str, human_feedback: str) -> str:
        """
        This LLM call generates a better instruction for the LLM that creates the AgentQL query
        """
        instructions = """
            You are an Expert Prompt Engineer. Your job is to improve scraping instructions.
            You will be given an ORIGINAL PROMPT that a user wrote, and the HUMAN FEEDBACK explaining why the resulting data was wrong.
            
            Your task is to merge the ORIGINAL PROMPT and the HUMAN FEEDBACK into a single, highly specific, bulletproof NEW PROMPT.
            
            RULES:
            1. ONLY output the new prompt text. No intros, no markdown, no explanations.
            2. The new prompt must explicitly state the rules from the feedback.
            3. Use clear English, even if the feedback is in Dutch.
        """

        dynamic_prompt = f"""
        ORIGINAL PROMPT:
        "{old_prompt}"

        HUMAN FEEDBACK (Why it failed):
        "{human_feedback}"

        Please write the NEW PROMPT.
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=dynamic_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instructions,
                    temperature=0.2
                )
            )
            
            return response.text.strip()
        except Exception as e:
            print(f"Meta-AI Crash: {e}")
            return None

    def process_rejected_job(self, job_type_id, old_prompt, feedback_reason):
        new_prompt = self.create_better_prompt(old_prompt, feedback_reason)
        
        if new_prompt:
            print(f"New prompt:\n{new_prompt}")
            
            
            response = requests.patch(f"http://localhost/api/scraper-job-types/{job_type_id}/prompt", json={
                "prompt": new_prompt
            })

            if response.status_code == 200:
                print("Prompt has been updated!")


if __name__ == "__main__":
    
    optimizer = FeedbackProcessor()
    
    test_old_prompt = "Create a agentql that fetches the usage per month"
    test_feedback = "The month and year were missing, so we have no idea which month the usage data belongs to. Also, we need the usage in kWh, not in Euros."
    
    print("\n" + "="*50)
    print(f"Old prompt: {test_old_prompt}")
    print(f"Feedback:    {test_feedback}")
    print("="*50 + "\n")
    
    print("Creating a better prompt\n")
    
    # 3. Vuur hem af!
    result = optimizer.create_better_prompt(test_old_prompt, test_feedback)
    
    # 4. Bewonder het resultaat
    if result:
        print("The new prompt:")
        print("-" * 50)
        print(result)
        print("-" * 50)
        print("\nStore in the database")
    else:
        print("Something went wrong with the LLM")