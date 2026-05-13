import json
from abc import ABC, abstractmethod

class BaseLLM(ABC):
    
    @abstractmethod
    def generate_query(self, prompt: str, schema: dict, max_retries: int = 3) -> str:
        pass

    @abstractmethod
    def optimize_failed_prompt(self, old_prompt: str, target_schema: dict, human_feedback: str, failed_output: str):
        pass


    def calculate_confidence(self, schema, results):
        if not schema or not results:
            return 0
            

        # create the recursive function to loop through the given data
        def evaluate_layer(curr_schema, curr_results):
            # if one of the 2 layers isnt a dictionary, we cannot check the keys so return 0 earned points and 0 total points
            if not isinstance(curr_schema, dict) or not isinstance(curr_results, dict):
                return 0, 0
                
            e_pts = 0
            t_pts = 0
            
            for key, expected_val in curr_schema.items():
                # a right key is given 2 points since it is the base of the schema
                t_pts += 2 
                
                # does the key exist and is it not empty -> give a point
                if key in curr_results and curr_results[key] is not None:
                    e_pts += 1
                    actual_val = curr_results[key]
                    
                    if isinstance(expected_val, list):
                        if isinstance(actual_val, list):
                            e_pts += 1
                            
                            # if it has a schema list structure with results, loop through the results and check them with the schema template
                            if len(expected_val) > 0 and len(actual_val) > 0:
                                for item in actual_val:
                                    sub_e, sub_t = evaluate_layer(expected_val[0], item)
                                    e_pts += sub_e
                                    t_pts += sub_t
                                    
                    # if it is a nested object, add a point for the right datatype
                    elif isinstance(expected_val, dict):
                        if isinstance(actual_val, dict):
                            e_pts += 1
                            sub_e, sub_t = evaluate_layer(expected_val, actual_val)
                            e_pts += sub_e
                            t_pts += sub_t
                            
                    # if it is a string, filter the words out and only get the first word which is the datatype
                    elif isinstance(expected_val, str):
                        base_type = expected_val.split(" ")[0].lower()
                        
                        if base_type == "string" and isinstance(actual_val, str):
                            e_pts += 1
                        elif base_type in ["integer", "decimal", "int", "float", "double"]:
                            try:
                                float(actual_val)
                                e_pts += 1
                            except (ValueError, TypeError):
                                pass
                        elif base_type == "boolean" and isinstance(actual_val, bool):
                            e_pts += 1
                        else:
                            e_pts += 1
                            
            return e_pts, t_pts

        # start the recursion
        earned, total = evaluate_layer(schema, results)
        
        if total == 0:
            return 100
            
        return int((earned / total) * 100)