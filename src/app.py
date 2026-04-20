import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai

# 1. Configuration & Model Setup
API_KEY = "AIzaSyD96ea1EbPQLv3nVXzB6JKDmlwgvMRFXG0" # Ensure your actual key is here
genai.configure(api_key=API_KEY)

# 2. Define Pulse's Tools (Agentic Capabilities)

def get_mesh_schema():
    """
    Scans the 'data' directory and returns the schema (column names) 
    for all available manufacturing datasets.
    """
    schemas = {}
    data_path = "data"
    if not os.path.exists(data_path):
        return "Error: 'data' folder not found."
    
    files = [f for f in os.listdir(data_path) if f.endswith((".csv", ".xlsx"))]
    if not files:
        return "The data mesh is empty. No CSV or XLSX files found."

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
    Reads the last 15 rows of a specific data file. 
    Pulse uses this to analyze actual values and find correlations.
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

# 3. Initialize Gemini with System Instructions and Tools
SYSTEM_PROMPT = (
    "You are Pulse, an expert Manufacturing Data Agent. "
    "Your goal is to find correlations and hidden errors in the data mesh. "
    "When asked a question, you must: "
    "1. Use 'get_mesh_schema' to see what data is available. "
    "2. Use 'read_data_sample' to pull the actual values for relevant files. "
    "3. Compare values across files (e.g., matching Dates or Lines) to find issues. "
    "Do not say you cannot access data; you have tools to read it."
)

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=[get_mesh_schema, read_data_sample],
    system_instruction=SYSTEM_PROMPT
)

# 4. Chainlit UI Logic

@cl.on_chat_start
async def start():
    # enable_automatic_function_calling is key for Pulse to use tools on its own
    chat = model.start_chat(enable_automatic_function_calling=True)
    cl.user_session.set("chat", chat)
    
    await cl.Message(content="### ⚡ Pulse: Agentic Data Mesh (G) is Online\nSystem instructions loaded. I am ready to correlate your mesh data.").send()

@cl.on_message
async def main(message: cl.Message):
    chat = cl.user_session.get("chat")
    
    # Quick Trend Visualization Logic
    if "trend" in message.content.lower():
        try:
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", 
                         title="Pulse Live: Production Trend",
                         template="plotly_dark")
            await cl.Message(content="Generating trend visualization...", 
                             elements=[cl.Plotly(name="chart", figure=fig)]).send()
            return
        except Exception as e:
            await cl.Message(content=f"Trend error: {e}").send()
            return

    # Agentic reasoning via Tool-calling
    try:
        response = chat.send_message(message.content)
        await cl.Message(content=response.text).send()
    except Exception as e:
        await cl.Message(content=f"Reasoning Error: {str(e)}").send()
