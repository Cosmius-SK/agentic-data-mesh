import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai

# 1. Initialize Google AI Studio (Free Tier)
genai.configure(api_key="AIzaSyD96ea1EbPQLv3nVXzB6JKDmlwgvMRFXG0")

# 2. Define the Tool Function
def get_mesh_schema():
    """Returns the column names and sample rows of all files in the data folder."""
    schemas = {}
    data_path = "data"
    if not os.path.exists(data_path):
        return "Error: 'data' folder not found."
    
    for file in os.listdir(data_path):
        if file.endswith((".csv", ".xlsx")):
            path = os.path.join(data_path, file)
            df = pd.read_csv(path, nrows=2) if file.endswith(".csv") else pd.read_excel(path, nrows=2)
            schemas[file] = list(df.columns)
    return schemas

# 3. Setup the Model with Tools
# Note: AI Studio handles tools slightly differently than Vertex AI
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[get_mesh_schema] 
)

@cl.on_chat_start
async def start():
    # Store the chat session in the user session
    chat = model.start_chat(enable_automatic_function_calling=True)
    cl.user_session.set("chat", chat)
    await cl.Message(content="Agentic Data Mesh (Pulse) is online. I'm ready!").send()

@cl.on_message
async def main(message: cl.Message):
    chat = cl.user_session.get("chat")
    
    # Check for manual trend logic first (as per your original design)
    if "trend" in message.content.lower():
        try:
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", title="Production Trend")
            await cl.Message(content="Here is the trend:", elements=[cl.Plotly(name="chart", figure=fig)]).send()
            return
        except Exception as e:
            await cl.Message(content=f"Error loading trend data: {e}").send()
            return

    # Send message to Gemini
    response = chat.send_message(message.content)
    
    # AI Studio with 'enable_automatic_function_calling' handles the tool execution for you!
    await cl.Message(content=response.text).send()
