import time
import json
from google import genai
from google.genai import types
from llm_providers.base_llm import BaseLLM

class GeminiProvider(BaseLLM):
    def __init__(self):
        self.client = genai.Client()   

    def generate_query(self, prompt: str, schema: dict, max_retries: int = 3):
        instructions = f"""
            You are an expert at writing AgentQL queries for web scraping. 
            AgentQL uses a GraphQL-like syntax to extract UI elements from a webpage. 
            
            CRITICAL RULES:
            - NEVER OUTPUT JSON! Do not use quotes (" or ') around field names.
            - NEVER use colons (:) to define arrays.
            - If a field is a list/array, put [] directly after the name with NO spaces.
            
            EXAMPLE OF WRONG OUTPUT (JSON):
            {{
                "month": [],
                "usage_per_day": []
            }}
            
            EXAMPLE OF CORRECT OUTPUT (AgentQL):
            {{
                month[]
                usage_per_day[]
            }}
            
            Respond ONLY with the raw AgentQL query block based on the user's intent. Do not include markdown code blocks.
        """

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=f"Write an AgentQL query to extract: {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction=instructions,
                        temperature=0.1
                    )
                )
                
                query = response.text.strip()
                if query.startswith("```"):
                    query = query.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                query = query.strip('\'"')

                return query

            except Exception as e:
                error_str = str(e).lower()
                
                if "429" in error_str or "quota" in error_str or "503" in error_str or "overloaded" in error_str:
                    wait_time = 2 ** attempt 
                    print(f"Gemini overloaded (retry {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"Gemini error: {e}")
                    break
                    
        print("Gemini fails after several retry attempts")
        return None

