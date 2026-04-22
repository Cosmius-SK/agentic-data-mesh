from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from google import genai
import os

class HiveState(TypedDict):
    query: str
    mesh_profile: List[Dict]
    plan: List[str]
    next_node: str
    output: str

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def planner_node(state: HiveState):
    prompt = f"""Analyze query: {state['query']}
    Data Context: {state['mesh_profile']}
    Available Skills: [skill_profiler, skill_plotter]
    Choose a skill or suggest 'custom_code'."""
    
    # Simple logic for Sprint 1
    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return {"plan": [response.text], "next_node": "executor"}

async def executor_node(state: HiveState):
    # Logic to map 'plan' to SovereignSkills
    return {"output": "Task completed by Skill Registry.", "next_node": END}

workflow = StateGraph(HiveState)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", END)
hive_engine = workflow.compile()
