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
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash-latest"

# 2. Define Pulse's Tools

def get_mesh_schema():
    """
    REQUIRED: Call this first to see which CSV files exist and their columns.
    """
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
    """
    REQUIRED: Call this to read actual data rows to find correlations or spikes.
    Args:
        filename (str): The name of the file to read.
    """
    data_path = "data"
    path = os.path.join(data_path, filename)
    if not os.path.exists(path):
        return f"Error: {filename} not found."

    try:
        df = pd.read_csv(path) if filename.endswith(".csv") else pd.read_excel(path)
        # Convert to dict for the new SDK's tool output
        return df.tail(15).to_dict(orient="records")
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"

# 3. System Instructions
SYSTEM_PROMPT = (
    "You are Pulse, an autonomous Manufacturing Intelligence Agent. "
    "You have tools to access a data mesh. You MUST follow this protocol:\n"
    "1. Always use 'get_mesh_schema' first to see what data is available.\n"
    "2. Always use 'read_data_sample' to look at specific rows for troubleshooting.\n"
    "3. NEVER say you cannot access data. Use your tools.\n"
    "4. Correlate insights across multiple files (e.g., Temperature vs. Vibration)."
)

# 4. Chainlit UI Logic

@cl.on_chat_start
async def start():
    # Pass function references to the session
    cl.user_session.set("tools", [get_mesh_schema, read_data_sample])
    await cl.Message(content="### ⚡ Pulse (v2.1) Secured & Online\nEnvironment variables loaded. Ready for correlation analysis.").send()

@cl.on_message
async def main(message: cl.Message):
    # Native Trend shortcut
    if "trend" in message.content.lower():
        try:
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", title="Pulse: Production Snapshot", template="plotly_dark")
            await cl.Message(content="Visualizing current production trend...", elements=[cl.Plotly(name="chart", figure=fig)]).send()
            return
        except Exception as e:
            await cl.Message(content=f"Trend error: {e}").send()
            return

    # Agentic Reasoning via Tool-calling
    try:
        tools = cl.user_session.get("tools")
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
        await cl.Message(content=f"Pulse reasoning failed: {str(e)}").send()
