import os
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

from data_store import DataStore
from file_processor import process_file
from agent import DataChatAgent

SUPPORTED_EXT = {'.csv', '.xlsx', '.xls', '.pdf', '.docx', '.pptx'}


# ── Session start ─────────────────────────────────────────────────────────────

@cl.on_chat_start
async def start():
    store = DataStore()
    cl.user_session.set("store", store)
    cl.user_session.set("history", [])

    loaded = store.list_files()
    if loaded:
        summary = store.get_context_summary()
        await cl.Message(
            content=(
                f"Welcome back.\n\n"
                f"I have **{len(loaded)} file(s)** ready to analyse:\n\n"
                f"{summary}\n\n"
                f"Upload more files or ask me anything."
            )
        ).send()
    else:
        starters = (
            "\n\n**Try asking:**\n"
            "- *\"What anomalies exist in this data?\"*\n"
            "- *\"Show me a chart of sales by month\"*\n"
            "- *\"Summarise the key findings from this report\"*\n"
            "- *\"Are there any missing values?\"*"
        )
        await cl.Message(
            content=(
                "Hello. I'm **Pulse**, your AI data partner.\n\n"
                "Attach a file — CSV, Excel, PDF, Word, or PowerPoint — and ask me anything about it."
                + starters
            )
        ).send()


# ── Incoming messages ─────────────────────────────────────────────────────────

@cl.on_message
async def main(message: cl.Message):
    store: DataStore = cl.user_session.get("store")
    history: list = cl.user_session.get("history")

    # ── 1. Handle file uploads ─────────────────────────────────────────────────
    new_files: list = []
    for el in message.elements or []:
        if not getattr(el, 'path', None):
            continue
        ext = Path(el.name).suffix.lower()
        if ext not in SUPPORTED_EXT:
            await cl.Message(
                content=f"⚠️ **{el.name}** — unsupported type. "
                        f"Supported: {', '.join(sorted(SUPPORTED_EXT))}"
            ).send()
            continue

        async with cl.Step(name=f"Loading {el.name}", type="tool") as step:
            try:
                fd = process_file(el.path)
                with open(el.path, 'rb') as f:
                    raw = f.read()
                store.add_file(fd, raw_bytes=raw)
                new_files.append(el.name)

                if fd.file_type == 'tabular':
                    df = fd.dataframe
                    cols = ', '.join(df.columns[:6].tolist())
                    more = f" … +{len(df.columns)-6} more" if len(df.columns) > 6 else ""
                    step.output = (
                        f"✅ {len(df):,} rows × {len(df.columns)} columns  \n"
                        f"Columns: {cols}{more}"
                    )
                elif fd.slides:
                    step.output = f"✅ {fd.metadata['slide_count']} slides extracted"
                elif fd.metadata and 'page_count' in fd.metadata:
                    tbl_note = f", {len(fd.tables)} tables" if fd.tables else ""
                    step.output = f"✅ {fd.metadata['page_count']} pages{tbl_note} extracted"
                else:
                    wc = fd.metadata.get('word_count', '?') if fd.metadata else '?'
                    tbl_note = f", {len(fd.tables)} tables" if fd.tables else ""
                    step.output = f"✅ ~{wc} words{tbl_note} extracted"

            except Exception as exc:
                step.output = f"❌ {exc}"

    query = message.content.strip()

    # Files uploaded but no question → show summary and stop
    if new_files and not query:
        await cl.Message(
            content=(
                f"Loaded **{len(new_files)} file(s)**.\n\n"
                f"{store.get_context_summary()}\n\n"
                "What would you like to know?"
            )
        ).send()
        return

    if not query:
        return

    # ── 2. Guard: need data and API key ───────────────────────────────────────
    if not store.list_files():
        await cl.Message(
            content="No data loaded yet. Attach a file to your message first."
        ).send()
        return

    if not os.getenv("GEMINI_API_KEY"):
        await cl.Message(
            content="⚠️ `GEMINI_API_KEY` is not set. Add it to your `.env` file and restart."
        ).send()
        return

    # ── 3. Run agent ──────────────────────────────────────────────────────────
    agent = DataChatAgent(store)
    thinking_msg = cl.Message(content="⏳ Thinking…")
    await thinking_msg.send()

    log: list = []
    charts: list = []
    final_text = ""

    async for event in agent.chat(query, history):
        kind = event[0]

        if kind == 'step':
            _, tool_name, args = event
            log.append(f"🔧 **{_tool_label(tool_name, args)}**")
            thinking_msg.content = '\n\n'.join(log)
            await thinking_msg.update()

        elif kind == 'step_result':
            _, _tool, result = event
            snippet = result.replace('\n', ' ')[:200]
            if log:
                log[-1] += f"\n  ↳ `{snippet}`"
                thinking_msg.content = '\n\n'.join(log)
                await thinking_msg.update()

        elif kind == 'chart':
            charts.append(event[1])

        elif kind == 'final':
            final_text = event[1]

        elif kind == 'error':
            final_text = f"❌ {event[1]}"

    # Remove thinking indicator and send final answer
    try:
        await thinking_msg.remove()
    except Exception:
        thinking_msg.content = ""
        await thinking_msg.update()

    elements = [
        cl.Plotly(name=f"chart_{i}", figure=fig, display="inline")
        for i, fig in enumerate(charts)
    ]
    await cl.Message(
        content=final_text or "Done.",
        elements=elements or None,
    ).send()

    # ── 4. Keep conversation history (question + final answer only) ───────────
    history.append(types.Content(role='user', parts=[types.Part(text=query)]))
    history.append(types.Content(role='model', parts=[types.Part(text=final_text)]))
    cl.user_session.set("history", history)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tool_label(tool_name: str, args: dict) -> str:
    if tool_name == "run_data_query":
        first_line = args.get("code", "").split('\n')[0][:70]
        return f"Running: {first_line}"
    if tool_name == "list_loaded_files":
        return "Listing loaded files"
    if tool_name == "get_file_details":
        return f"Inspecting `{args.get('filename', '')}`"
    if tool_name == "search_document":
        return f"Searching `{args.get('filename', '')}` for '{args.get('query', '')}'"
    return tool_name
