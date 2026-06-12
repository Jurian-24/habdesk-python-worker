import os
import json
import requests

class OllamaProvider:
    def __init__(self):
        self.client = None
        self.endpoint = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    
    def generate_query(self, prompt: str, schema: dict, max_retries: int = 3):
        print("komt in generate query")
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

                payload = {
                    "model": "llama3.1",
                    "prompt": dynamic_prompt,
                    "stream": False
                }

                response = requests.post(f"{self.endpoint}/api/generate", json=payload)

                print(response.json())

                if response.status_code == 200:
                    return response.json().get('response')
                else:
                    return f"Fout: {response.status_code} - {response.text}"
            except Exception as e:
                print(e)
    
    def _serialize_query(self, query: str):
        pass

    def create_query_test(self, prompt):
        dynamic_prompt = f"""
            You are an AgentQL query generator. AgentQL is NOT GraphQL.

            AgentQL syntax rules:
            - Arrays use [] notation: products[]
            - No "edges", "nodes", "node" wrappers
            - No markdown, no backticks, no explanation
            - Only return the raw query, nothing else

            PRIMARY INSTRUCTION: {prompt}

            EXAMPLE of valid AgentQL:
            query {{
                products[] {{
                    product_name
                    product_price
                }}
            }}

            Now generate the query for the instruction above. RAW QUERY ONLY.
        """
        payload = {
            "model": "llama3.1",
            "prompt": dynamic_prompt,
            "stream": False
        }

        response = requests.post(f"{self.endpoint}/api/generate", json=payload)

        if response.status_code == 200:
            return response.json().get('response')
        else:
            return f"Fout: {response.status_code} - {response.text}"