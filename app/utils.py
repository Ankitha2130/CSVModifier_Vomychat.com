import pandas as pd
from openai import OpenAI
from typing import Dict, List, Tuple
import logging
import json

logger = logging.getLogger(__name__)

class AIDataProcessor:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def _get_ai_instructions(self, user_prompt: str, df_info: Dict) -> Dict:
        """Get structured instructions from AI based on user prompt"""
        try:
            system_prompt = """
            You are a data processing assistant. Analyze the user's instructions and provide a JSON response with specific actions to modify the dataframe.
            Available operations: remove_duplicates, format_numbers, add_rows, delete_rows, filter_data
            Response format:
            {
                "operations": [
                    {
                        "type": "operation_name",
                        "params": {specific parameters for the operation}
                    }
                ]
            }
            """
            
            context = f"DataFrame info: {json.dumps(df_info)}"
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{context}\nInstructions: {user_prompt}"}
                ]
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error getting AI instructions: {str(e)}")
            raise

    def _get_dataframe_info(self, df: pd.DataFrame) -> Dict:
        """Get relevant dataframe information for AI context"""
        return {
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "row_count": len(df),
            "sample_data": df.head(2).to_dict(orient='records')
        }

    def process_dataframe(self, df: pd.DataFrame, user_prompt: str) -> Tuple[pd.DataFrame, List[str]]:
        """Process dataframe based on user instructions"""
        logs = []
        try:
            # Get dataframe info for AI context
            df_info = self._get_dataframe_info(df)
            
            # Get AI instructions
            instructions = self._get_ai_instructions(user_prompt, df_info)
            
            # Process each operation
            for operation in instructions["operations"]:
                op_type = operation["type"]
                params = operation["params"]
                
                if op_type == "remove_duplicates":
                    subset = params.get("columns", None)
                    df = df.drop_duplicates(subset=subset)
                    logs.append(f"Removed duplicates {f'on columns {subset}' if subset else ''}")
                
                elif op_type == "format_numbers":
                    for column in params["columns"]:
                        format_str = params["format"]
                        df[column] = df[column].apply(lambda x: format_str.format(float(x)))
                    logs.append(f"Formatted numbers in columns {params['columns']}")
                
                elif op_type == "add_rows":
                    new_rows = pd.DataFrame(params["rows"])
                    df = pd.concat([df, new_rows], ignore_index=True)
                    logs.append(f"Added {len(params['rows'])} new rows")
                
                elif op_type == "delete_rows":
                    condition = params["condition"]
                    mask = df.eval(condition)
                    df = df[~mask]
                    logs.append(f"Deleted rows where {condition}")
                
                elif op_type == "filter_data":
                    condition = params["condition"]
                    mask = df.eval(condition)
                    df = df[mask]
                    logs.append(f"Filtered data where {condition}")
            
            return df, logs
            
        except Exception as e:
            logger.error(f"Error processing dataframe: {str(e)}")
            logs.append(f"Error: {str(e)}")
            raise 