import chainlit as cl
import pandas as pd
import plotly.express as px
import os
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration

# 1. Initialize Vertex AI
PROJECT_ID = "your-gcp-project" # Update this!
aiplatform.init(project=aisk2026, location="us-central1")

# 2. Define Tools (Functions Gemini can call)
def get_mesh_schema():
    """Returns the column names and sample rows of all files in the data folder."""
    schemas = {}
    for file in os.listdir("data"):
        if file.endswith((".csv", ".xlsx")):
            df = pd.read_csv(f"data/{file}", nrows=2) if file.endswith(".csv") else pd.read_excel(f"data/{file}", nrows=2)
            schemas[file] = list(df.columns)
    return schemas

# Wrap tools for Gemini
mesh_tool = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="get_mesh_schema",
            description="Get the structure of all available manufacturing spreadsheets",
            parameters={"type": "object", "properties": {}}
        )
    ]
)

model = GenerativeModel("gemini-1.5-flash-002", tools=[mesh_tool]) # Gemini 2.5/1.5 Flash

@cl.on_chat_start
async def start():
    await cl.Message(content="Agentic Data Mesh (G) is online. I'm ready to analyze your manufacturing floor data.").send()

@cl.on_message
async def main(message: cl.Message):
    # Start the Agentic Reasoning
    chat = model.start_chat()
    
    # Step 1: Gemini decides if it needs to see the schema
    response = chat.send_message(message.content)
    
    # Check for Function Calls (Agentic Behavior)
    if response.candidates[0].function_calls:
        for call in response.candidates[0].function_calls:
            if call.name == "get_mesh_schema":
                # Show the user the agent is 'thinking'
                async with cl.Step(name="Inspecting Mesh Structure"):
                    schema_info = get_mesh_schema()
                    # Feed back to Gemini
                    final_response = chat.send_message(f"The schemas are: {schema_info}. Now answer the user's question or ask for clarification on keys.")
                    await cl.Message(content=final_response.text).send()
    else:
        # Standard trend chart logic
        if "trend" in message.content.lower():
            df = pd.read_csv("data/daily_production.csv")
            fig = px.line(df, x="Date", y="Qty_Produced", title="Production Trend")
            await cl.Message(content="Here is the trend:", elements=[cl.Plotly(name="chart", figure=fig)]).send()
        else:
            await cl.Message(content=response.text).send()
