import chainlit as cl
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Load Secrets & Initialize Client
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

# Initialize the NEW client
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash"

# 2. Define Pulse's Tools
def get_mesh_schema():
    """REQUIRED: Call this first to see which CSV files exist and their columns."""
    schemas = {}
    data_path = "data"
    if not os.path.exists(data_path):
        return {"error": "data folder not found"}
    
    files = [f for f in os.listdir(data_path) if f.endswith((".csv", ".xlsx"))]
    for file in files:
        path = os.path.join(data_path, file)
        try:
            df = pd.read_csv(path, nrows=0) if file.endswith(".csv") else pd.read_excel(path, nrows=0)
            schemas[file] = list(df.columns)
        except Exception as e:
            schemas[file] = f"Error: {str(e)}"
    return schemas

def read_data_sample(filename: str):
    """REQUIRED: Call this to read actual data rows to find correlations or spikes."""
    data_path = "data"
    path = os.path.join(data_path, filename)
    if not os.path.exists(path):
        return f"Error: {filename} not found."
    try:
        df = pd.read_csv(path) if filename.endswith(".csv") else pd.read_excel(path)
        return df.tail(15).to_dict(orient="records")
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"

# 3. System Instructions
SYSTEM_PROMPT = (
    "You are Pulse, an autonomous Manufacturing Intelligence Agent. "
    "Use your tools to access the data mesh. ALWAYS call get_mesh_schema first. "
    "NEVER say you cannot access data."
)

# 4. Chainlit UI Logic
@cl.on_chat_start
async def start():
    # Pass function references (the actual functions) to the session
    cl.user_session.set("tools", [get_mesh_schema, read_data_sample])
    await cl.Message(content="### ⚡ Pulse (v2.2) Clean Boot\nUsing NEW SDK and secured .env key.").send()

@cl.on_message
async def main(message: cl.Message):
    try:
        tools = cl.user_session.get("tools")
        # USE THE NEW CLIENT CALL (client.models.generate_content)
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=message.content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(max_remote_calls=5)
            )
        )
        await cl.Message(content=response.text).send()
    except Exception as e:
        await cl.Message(content=f"Pulse failed: {str(e)}").send()
