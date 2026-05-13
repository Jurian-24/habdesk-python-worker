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
                dynamic_prompt = f"""
                    You need to write an AgentQL query. 
                    
                    PRIMARY INSTRUCTION (The absolute source of truth):
                    {prompt}
                    
                    SUGGESTED TARGET SCHEMA (Format guidelines):
                    {json.dumps(schema)}
                    
                    RULES:
                    1. Your ultimate goal is to fulfill the PRIMARY INSTRUCTION. 
                    2. Try to map your extraction to the keys in the SUGGESTED TARGET SCHEMA if they match the instruction.
                    3. If the schema is completely irrelevant to the instruction (e.g. instruction asks for 'title' but schema has 'month'), IGNORE THE SCHEMA and use highly descriptive field names that AgentQL can use to find the actual elements requested in the instruction.
                """
                response = self.client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=dynamic_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=instructions,
                        temperature=0.1
                    )
                )
                
                query = response.text.strip()
                if query.startswith("```"):
                    query = query.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                query = query.strip('\'"')
                
                query = query.replace('\n', ' ').replace('\r', '')
                query = " ".join(query.split())
                
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

    def optimize_failed_prompt(self, old_prompt, target_schema, human_feedback, failed_output):
        instructions = """
            You are a Master Prompt Engineer for an AgentQL web scraping system.
            Your job is to rewrite a scraping prompt that failed, based on human feedback.
            
            RULES:
            1. ONLY output the new, rewritten prompt. No explanations, no markdown blocks, no intro text.
            2. Make the new prompt highly specific so it strictly extracts the data requested.
            3. Ensure the new prompt considers the human feedback explicitly to avoid repeating the mistake.
        """