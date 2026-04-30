import json
from abc import ABC, abstractmethod

class BaseLLM(ABC):
    
    @abstractmethod
    def generate_query(self, prompt: str, schema: dict, max_retries: int = 3) -> str:
        pass


    def calculate_confidence(self, schema: dict, results: dict) -> int:
        if not schema or not results:
            return 0
            
        # create sets for the keys for a faster comparison
        expected_keys = set(schema.keys())
        actual_keys = set(results.keys())
        
        # which keys are overlapping
        matching_keys = expected_keys.intersection(actual_keys)
        
        total_points = len(expected_keys) * 2
        earned_points = 0
        
        for key in matching_keys:
            value = results[key]
            
            # check if the value is not empty
            if value: 
                earned_points += 1
                
                # check the datatype
                expected_type = schema[key].lower()
                
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
                    # if there is a unkown data type, give it the benefit of the doubt
                    earned_points += 1
                    
        # prevent the dividing by 0
        if total_points == 0:
            return 100
            
        return int((earned_points / total_points) * 100)