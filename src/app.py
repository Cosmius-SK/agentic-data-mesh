import chainlit as cl
import pandas as pd
import plotly.express as px
from google.cloud import aiplatform

# Setup Gemini 2.5 Flash
aiplatform.init(project="your-gcp-project", location="us-central1") # Vertex AI endpoint

@cl.on_chat_start
async def start():
    cl.user_session.set("data", pd.read_csv("data/daily_production.csv"))
    await cl.Message(content="Agentic Data Mesh is live. How can I help with your manufacturing data today?").send()

@cl.on_message
async def main(message: cl.Message):
    data = cl.user_session.get("data")
    
    # Simple Logic: If user asks for a 'trend' or 'chart'
    if "trend" in message.content.lower():
        # Let's say we plot daily production
        fig = px.line(data, x="Date", y="Qty_Produced", title="Production Trend")
        
        # This renders the chart directly in the chat
        elements = [cl.Plotly(name="chart", figure=fig, display="inline")]
        await cl.Message(content="Here is the production trend you requested:", elements=elements).send()
    else:
        # Pass to Gemini 2.5 Flash for reasoning
        # (Function calling logic goes here)
        await cl.Message(content="I'm analyzing the relationships in your spreadsheets...").send()
