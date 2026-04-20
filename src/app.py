import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3-flash-preview"

# --- AGENT TELEMETRY HELPER ---
def agent_log_sync(agent_name, message):
    """Sends a status update to the UI synchronously."""
    # We use cl.run_sync to bridge the gap between AI threads and Chainlit's async UI
    cl.run_sync(cl.Message(content=f"_{agent_name} is {message}..._").send())

# --- ACTUAL AGENT TOOLS (Now Synchronous for Auto-Calling) ---

def get_mesh_schema():
    """DATA AGENT: Scans the mesh to see available files and columns."""
    agent_log_sync("Data Agent", "mapping the current data mesh nodes")
    data_path = "data"
    schemas = {}
    if not os.path.exists(data_path): return "Error: Data folder missing."
    for file in os.listdir(data_path):
        if file.endswith((".csv", ".xlsx")):
            df = pd.read_csv(os.path.join(data_path, file), nrows=0) if file.endswith(".csv") else pd.read_excel(os.path.join(data_path, file), nrows=0)
            schemas[file] = list(df.columns)
    return schemas

def fetch_and_analyze_data(filename: str, query_focus: str):
    """DATA AGENT: Retrieves and correlates data from a specific node."""
    agent_log_sync("Data Agent", f"extracting metrics from {filename}")
    time.sleep(1) # Visual delay for demo
    df = pd.read_csv(os.path.join("data", filename))
    return df.tail(15).to_dict(orient="records")

def generate_visualization(data_json_str: str, x: str, y: str, title: str):
    """VIZ AGENT: Creates dynamic Plotly charts based on worker input."""
    agent_log_sync("Viz Agent", f"designing interactive chart for {title}")
    import json
    data = json.loads(data_json_str) if isinstance(data_json_str, str) else data_json_str
    df = pd.DataFrame(data)
    
    fig = px.line(df, x=x, y=y, title=title, template="plotly_dark")
    if "Vibration" in y: fig.add_hline(y=7.0, line_dash="dash", line_color="red")
    
    cl.run_sync(cl.Message(content=f"### 📈 Specialist Output", 
                          elements=[cl.Plotly(name="chart", figure=fig, display="inline")]).send())
    return "Visualization deployed."

def create_maintenance_report(analysis_summary: str):
    """DOC AGENT: Persists findings into a physical markdown report."""
    agent_log_sync("Doc Agent", "finalizing maintenance documentation")
    filename = f"pulse_report_{datetime.now().strftime('%H%M%S')}.md"
    with open(filename, "w") as f:
        f.write(f"# AGENTIC MESH ANALYSIS\n{analysis_summary}")
    return f"Report committed to disk as {filename}"

# --- THE ORCHESTRATOR ---

@cl.on_chat_start
async def start():
    await cl.Message(content="### ⚡ Pulse Online\nIntelligent Agentic Data Mesh").send()

@cl.on_message
async def main(message: cl.Message):
    # Register the Sync Tools
    tools = [get_mesh_schema, fetch_and_analyze_data, generate_visualization, create_maintenance_report]
    
    instruction = (
        "You are the Orchestrator for Pulse. "
        "1. Start by calling get_mesh_schema to verify available data. "
        "2. Only invoke the necessary agents (Data, Viz, or Doc) based on the user's specific request. "
        "3. If the user asks for 'what is available', do not use Viz or Doc agents. "
        "4. Combine agent outputs into a concise, professional 'Managerial' summary."
    )

    try:
        # LLM reasoning happens here
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=message.content,
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig()
            )
        )
        if response.text:
            await cl.Message(content=response.text).send()
    except Exception as e:
        await cl.Message(content=f"❌ Orchestration Error: {str(e)}").send()
