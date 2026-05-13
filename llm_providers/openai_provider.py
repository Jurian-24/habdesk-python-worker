import os
import json
from openai import OpenAI
from dotenv import load_dotenv

class OpenAIProvider:
    def __init__(self):
        load_dotenv()
        
        self.client = OpenAI()
        
        self.default_model = "gpt-4o-mini" 

    def generate_query(self, prompt: str, target_schema: dict) -> str:
        """
        Vertaalt de menselijke prompt + schema naar een rauwe AgentQL query.
        """
        instructions = """
            You are an expert AgentQL query generator.
            Your job is to generate a valid AgentQL query based on the user's prompt and the target schema.
            ONLY output the raw query. No markdown formatting, no explanation, no json wrapping.
        """

        dynamic_prompt = f"""
            PRIMARY INSTRUCTION:
            {prompt}

            SUGGESTED TARGET SCHEMA:
            {json.dumps(target_schema)}

            RULES:
            1. Try to map your extraction to the keys in the SUGGESTED TARGET SCHEMA.
            2. If the schema is irrelevant, ignore it and use highly descriptive keys.
            3. Output ONLY the raw AgentQL query, e.g. {{ title, table {{ rows[] }} }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": dynamic_prompt}
                ],
                temperature=0.1 # Laag houden voor strakke, voorspelbare AgentQL code
            )
            
            query = response.choices[0].message.content.strip()

            # Veiligheidsslot: Strip markdown backticks mocht OpenAI eigenwijs zijn
            if query.startswith("```"):
                query = query.split("\n", 1)[1].rsplit("\n", 1)[0]
                
            return query.strip()

        except Exception as e:
            print(f"OpenAI crash: {e}")
            return None

    def create_better_prompt(self, old_prompt: str, human_feedback: str) -> str:
        """
        De "Meta-AI" functie die leert van jouw afkeuringen en de prompt herschrijft.
        """
        instructions = """
            You are an Expert Prompt Engineer. Your job is to improve scraping instructions.
            You will be given an ORIGINAL PROMPT that a user wrote, and the HUMAN FEEDBACK explaining why the resulting data was wrong.
            Your task is to merge the ORIGINAL PROMPT and the HUMAN FEEDBACK into a single, highly specific, bulletproof NEW PROMPT.
            RULES:
            1. ONLY output the new prompt text. No intros, no markdown, no explanations.
            2. The new prompt must explicitly state the rules from the feedback.
        """

        dynamic_prompt = f"""
            ORIGINAL PROMPT:
            "{old_prompt}"

            HUMAN FEEDBACK (Why it failed):
            "{human_feedback}"

            Please write the NEW PROMPT.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": dynamic_prompt}
                ],
                temperature=0.2 
            )
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(e)
            return None