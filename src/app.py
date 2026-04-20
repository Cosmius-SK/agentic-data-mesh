import chainlit as cl
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai

# 1. Initialize Google AI Studio (Free Tier)
# REPLACE THE KEY BELOW WITH YOUR ACTUAL KEY
genai.configure(api_key="AIzaSyD96ea1EbPQLv3nVXzB6JKDmlwgvMRFXG0")

def get_mesh_schema():
    """Returns the column names of all files in the data folder."""
    schemas = {}
    data_path = "data"
    if not os.path.exists(data_path):
        return "Error: 'data' folder not found."
    
    for file in os.listdir(data_path):
        if file.endswith((".csv", ".xlsx")):
            path = os.path.join(data_path, file)
            df = pd.read_csv(path, nrows=1) if file.endswith(".csv") else pd.read_excel(path, nrows=1)
            schemas[file] = list(df.columns)
    return schemas

# Setup the Model with Tools
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=[get_mesh_schema] 
)

@cl.on_chat_start
async def start():
    chat = model.start_chat(enable_automatic_function_calling=True)
    cl.user_session.set("chat", chat)
    await cl.Message(content="Agentic Data Mesh (Pulse) is online").send()

@cl.on_message
async def main(message: cl.Message):
    chat = cl.user_session.get("chat")
    
    if "trend" in message.content.lower():
        df = pd.read_csv("data/daily_production.csv")
        fig = px.line(df, x="Date", y="Qty_Produced", title="Production Trend")
        await cl.Message(content="Here is the trend:", elements=[cl.Plotly(name="chart", figure=fig)]).send()
        return

    response = chat.send_message(message.content)
    await cl.Message(content=response.text).send()
