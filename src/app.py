import os
import re
import asyncio
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests as _req
import chainlit as cl
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

from data_store import DataStore
from file_processor import process_file
from agent import DataChatAgent

SUPPORTED_EXT = {'.csv', '.xlsx', '.xls', '.pdf', '.docx', '.pptx'}
UPLOAD_DIR = "data/uploads"

# ── URL detection ──────────────────────────────────────────────────────────────
# Matches http(s) URLs that contain a recognisable data file extension,
# including CDC-style  rows.csv?accessType=DOWNLOAD  patterns.
_URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
_EXT_RE = re.compile(
    r'\.(csv|xlsx|xls|pdf|docx|pptx)(\?|&|#|$)',
    re.IGNORECASE,
)
_KEYWORD_RE = re.compile(
    r'(rows\.csv|download|export)[^\s]*',
    re.IGNORECASE,
)

def _find_data_url(text: str):
    """Return (url, ext) for the first data URL found in text, else None."""
    for url in _URL_RE.findall(text):
        m = _EXT_RE.search(url)
        if m:
            return url, '.' + m.group(1).lower()
        if _KEYWORD_RE.search(url):
            return url, '.csv'
    return None


def _download_file(url: str) -> tuple[str, str]:
    """
    Blocking download of url into UPLOAD_DIR.
    Returns (local_path, human_readable_size).
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Derive a clean filename from the URL path
    parsed = urlparse(url)
    raw_name = unquote(parsed.path.rstrip('/').split('/')[-1]) or 'download'
    # Strip query fragments that got absorbed into the name
    raw_name = raw_name.split('?')[0]
    if not Path(raw_name).suffix:
        raw_name += '.csv'

    dest = os.path.join(UPLOAD_DIR, raw_name)

    resp = _req.get(
        url, stream=True, timeout=300,
        headers={'User-Agent': 'Mozilla/5.0 (Pulse/1.0)'},
        allow_redirects=True,
    )
    resp.raise_for_status()

    total = int(resp.headers.get('content-length', 0))
    downloaded = 0
    with open(dest, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=131072):  # 128 KB chunks
            fh.write(chunk)
            downloaded += len(chunk)

    size_str = (
        f"{downloaded / 1_048_576:.1f} MB"
        if downloaded > 1_048_576
        else f"{downloaded // 1024} KB"
    )
    return dest, size_str


# ── Session start ──────────────────────────────────────────────────────────────

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
                f"Upload more files, paste a download URL, or ask me anything."
            )
        ).send()
    else:
        await cl.Message(
            content=(
                "Hello. I'm **Pulse**, your AI data partner.\n\n"
                "**To load data, you can:**\n"
                "- Attach a file (CSV, Excel, PDF, Word, PPT)\n"
                "- Paste a direct download URL\n\n"
                "**Try asking:**\n"
                "- *\"What anomalies exist in this data?\"*\n"
                "- *\"Show me a chart of values by category\"*\n"
                "- *\"Summarise the key findings from this report\"*\n"
                "- *\"Are there any missing values?\"*"
            )
        ).send()


# ── Incoming messages ──────────────────────────────────────────────────────────

@cl.on_message
async def main(message: cl.Message):
    store: DataStore = cl.user_session.get("store")
    history: list = cl.user_session.get("history")
    new_files: list = []

    # ── 1a. Handle attached file uploads ──────────────────────────────────────
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
                step.output = _ingest_summary(fd)
            except Exception as exc:
                step.output = f"❌ {exc}"

    # ── 1b. Detect & download data URLs in the message ─────────────────────────
    query = message.content.strip()
    url_hit = _find_data_url(query)

    if url_hit:
        url, ext = url_hit
        async with cl.Step(name="Downloading file from URL…", type="tool") as step:
            try:
                step.output = "⏳ Connecting…"
                local_path, size_str = await asyncio.to_thread(_download_file, url)
                step.output = f"⏳ Downloaded {size_str}, parsing…"
                fd = process_file(local_path)
                store.add_file(fd)  # already on disk — no need to re-write raw bytes
                fname = Path(local_path).name
                new_files.append(fname)
                step.output = f"✅ {size_str} downloaded — {_ingest_summary(fd)}"
            except Exception as exc:
                step.output = f"❌ Download failed: {exc}"

        # Strip the URL from the query so the agent doesn't try to fetch it again
        query = _URL_RE.sub('', query).strip()

    # Files loaded but no follow-up question → show summary and stop
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

    # ── 2. Guards ─────────────────────────────────────────────────────────────
    if not store.list_files():
        await cl.Message(
            content=(
                "No data loaded yet.\n\n"
                "You can:\n"
                "- Attach a file to your message\n"
                "- Paste a direct download URL (e.g. from data.cdc.gov, Kaggle, etc.)"
            )
        ).send()
        return

    if not os.getenv("GEMINI_API_KEY"):
        await cl.Message(
            content="⚠️ `GEMINI_API_KEY` is not set. Add it to your `.env` file and restart."
        ).send()
        return

    # ── 3. Run agent ───────────────────────────────────────────────────────────
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

    # ── 4. Persist conversation history ───────────────────────────────────────
    history.append(types.Content(role='user', parts=[types.Part(text=query)]))
    history.append(types.Content(role='model', parts=[types.Part(text=final_text)]))
    cl.user_session.set("history", history)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ingest_summary(fd) -> str:
    if fd.file_type == 'tabular':
        df = fd.dataframe
        cols = ', '.join(df.columns[:6].tolist())
        more = f" … +{len(df.columns)-6} more" if len(df.columns) > 6 else ""
        return f"{len(df):,} rows × {len(df.columns)} cols — {cols}{more}"
    if fd.slides:
        return f"{fd.metadata['slide_count']} slides extracted"
    if fd.metadata and 'page_count' in fd.metadata:
        extra = f", {len(fd.tables)} tables" if fd.tables else ""
        return f"{fd.metadata['page_count']} pages{extra}"
    wc = fd.metadata.get('word_count', '?') if fd.metadata else '?'
    extra = f", {len(fd.tables)} tables" if fd.tables else ""
    return f"~{wc} words{extra}"


def _tool_label(tool_name: str, args: dict) -> str:
    if tool_name == "run_data_query":
        return f"Running: {args.get('code', '').split(chr(10))[0][:70]}"
    if tool_name == "list_loaded_files":
        return "Listing loaded files"
    if tool_name == "get_file_details":
        return f"Inspecting `{args.get('filename', '')}`"
    if tool_name == "search_document":
        return f"Searching `{args.get('filename', '')}` for '{args.get('query', '')}'"
    return tool_name
