import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai

# 1. Configuration & Model Setup
API_KEY = "AIzaSyD96ea1EbPQLv3nVXzB6JKDmlwgvMRFXG0"
genai.configure(api_key=API_KEY)

# 2. Define Pulse's Tools (Agentic Capabilities)

def get_mesh_schema():
    """
    REQUIRED: Call this first to see which CSV files exist and what their columns are.
    Returns: A dictionary of {filename: [columns]}.
    """
    schemas = {}
    data_path = "data"
    if not os.path.exists(data_path):
        return "Error: 'data' folder not found."
    
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
    REQUIRED: Call this to read the actual rows of a file. 
    Use this to find correlations, spikes, or errors in the data.
    Args:
        filename (str): The name of the file to read (e.g., 'energy_consumption.csv').
    """
    data_path = "data"
    path = os.path.join(data_path, filename)
    if not os.path.exists(path):
        return f"Error: File {filename} not found."

    try:
        df = pd.read_csv(path) if filename.endswith(".csv") else pd.read_excel(path)
        return df.tail(15).to_string()
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"

# 3. Initialize Gemini with Strict System Instructions
SYSTEM_PROMPT = (
    "You are Pulse, an autonomous Manufacturing Intelligence Agent. "
    "You have access to a data mesh via tools. You MUST follow this protocol:\n"
    "1. Always call 'get_mesh_schema' first to identify relevant files.\n"
    "2. Always call 'read_data_sample' for any file that might contain the answer.\n"
    "3. NEVER say you cannot access data. Use your tools to see it.\n"
    "4. Correlate data across multiple files to find hidden insights."
)

# Using 1.5-flash-latest for better tool-calling reliability
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest', 
    tools=[get_mesh_schema, read_data_sample],
    system_instruction=SYSTEM_PROMPT
)

# 4. Chainlit UI Logic

@cl.on_chat_start
async def start():
    # Force automatic function calling
    chat = model.start_chat(enable_automatic_function_calling=True)
    cl.user_session.set("chat", chat)
    await cl.Message(content="### ⚡ Pulse (G): Agentic Correlator Online\nI am ready to inspect your data folders and find hidden issues.").send()

@cl.on_message
async def main(message: cl.Message):
    chat = cl.user_session.get("chat")
    
    # Visualization Shortcut
    if "trend" in message.content.lower():
        try:
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", title="Pulse: Production Trend", template="plotly_dark")
            await cl.Message(content="Visualizing production trend...", elements=[cl.Plotly(name="chart", figure=fig)]).send()
            return
        except Exception as e:
            await cl.Message(content=f"Trend error: {e}").send()
            return

    # Agentic Reasoning
    try:
        # Note: We send the message and Pulse handles tool-calling automatically
        response = chat.send_message(message.content)
        await cl.Message(content=response.text).send()
    except Exception as e:
        await cl.Message(content=f"Pulse reasoning failed: {str(e)}").send()
