import chainlit as cl
from orchestrator import hive_engine
from utils import get_local_mesh_profile, get_ram_usage
import os

@cl.on_chat_start
async def start():
    if not os.path.exists("data/pulse_generated"):
        os.makedirs("data/pulse_generated")
    await cl.Message(content="⚡ **Sovereign Hive OS v1.0 Online** (RAM Aware)").send()

@cl.on_message
async def main(message: cl.Message):
    state = {
        "query": message.content,
        "mesh_profile": get_local_mesh_profile(),
        "plan": [],
        "next_node": "",
        "output": ""
    }

    async with cl.Step(name="Hive Orchestrator", type="run") as master_step:
        async for event in hive_engine.astream(state):
            for node_name, output in event.items():
                async with cl.Step(name=f"Agent: {node_name}", type="tool") as sub_step:
                    sub_step.output = f"RAM: {get_ram_usage():.1f}MB | Action: {output.get('next_node', 'Finalizing')}"

    await cl.Message(content=f"### Hive Analysis Result\nSuccessfully processed mesh data.").send()
