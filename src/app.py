import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai

# 1. Configuration & Model Setup
# Make sure to replace with your actual API Key from AI Studio
API_KEY = "AIzaSyD96ea1EbPQLv3nVXzB6JKDmlwgvMRFXG0"
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
        return "Error: 'data' folder not found in the root directory."
    
    files = [f for f in os.listdir(data_path) if f.endswith((".csv", ".xlsx"))]
    if not files:
        return "The data mesh is currently empty. No CSV or XLSX files found."

    for file in files:
        path = os.path.join(data_path, file)
        try:
            # Read only the header to save memory/speed
            df = pd.read_csv(path, nrows=0) if file.endswith(".csv") else pd.read_excel(path, nrows=0)
            schemas[file] = list(df.columns)
        except Exception as e:
            schemas[file] = f"Error reading schema: {str(e)}"
            
    return schemas

def read_data_sample(filename: str):
    """
    Reads the last 15 rows of a specific data file. 
    Pulse uses this to correlate trends or find errors within the data.
    """
    data_path = "data"
    path = os.path.join(data_path, filename)
    
    if not os.path.exists(path):
        return f"Error: File {filename} not found."

    try:
        df = pd.read_csv(path) if filename.endswith(".csv") else pd.read_excel(path)
        # Return the tail as a string so Gemini can 'read' the values
        return df.tail(15).to_string()
    except Exception as e:
        return f"Error reading data from {filename}: {str(e)}"

# 3. Initialize Gemini with Tool-Calling enabled
# Using 1.5-flash-latest or gemini-2.0-flash (if your key supports it)
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=[get_mesh_schema, read_data_sample]
)

# 4. Chainlit UI Logic

@cl.on_chat_start
async def start():
    # Initialize a stateful chat session with automatic function calling
    chat = model.start_chat(enable_automatic_function_calling=True)
    cl.user_session.set("chat", chat)
    
    welcome_msg = (
        "### ⚡ Pulse: Agentic Data Mesh Online\n"
        "I am now monitoring your manufacturing data. I can:\n"
        "* **Scan** your data mesh for schemas.\n"
        "* **Correlate** errors across multiple datasets.\n"
        "* **Visualize** production trends."
    )
    await cl.Message(content=welcome_msg).send()

@cl.on_message
async def main(message: cl.Message):
    chat = cl.user_session.get("chat")
    
    # 5. Native Trend Visualization Shortcut
    # If the user asks for a 'trend' explicitly, we provide the Plotly Chart
    if "trend" in message.content.lower():
        try:
            # Note: Hardcoded to daily_production.csv for the shortcut
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", 
                         title="Pulse Snapshot: Production Trend",
                         template="plotly_dark")
            
            await cl.Message(
                content="Analyzing the production trend for you, SK.",
                elements=[cl.Plotly(name="production_chart", figure=fig)]
            ).send()
            return
        except Exception as e:
            await cl.Message(content=f"Trend Visualization Error: {e}").send()
            return

    # 6. Agentic Reasoning Loop
    # Gemini will decide whether to call get_mesh_schema or read_data_sample
    try:
        response = chat.send_message(message.content)
        await cl.Message(content=response.text).send()
    except Exception as e:
        await cl.Message(content=f"An error occurred during reasoning: {str(e)}").send()
