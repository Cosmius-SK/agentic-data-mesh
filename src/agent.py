import os
import asyncio
import json
from typing import AsyncGenerator, Dict, Optional, Tuple

import plotly.graph_objects as go
from google import genai
from google.genai import types

from data_store import DataStore, _safe_var
from code_executor import execute_data_code


# Max tool-call turns before we force a text-only final response
MAX_TURNS = 12
FORCE_FINALIZE_AT = 9   # after this many tool turns, strip tools from config


SYSTEM_PROMPT = """You are Pulse, an AI-powered data partner. Users upload files (CSV, Excel, PDF, Word, PPT) and you help them explore, analyse, and draw insights from their data.

Available tools:
1. list_loaded_files — See all loaded files, variable names, and structure
2. get_file_details(filename) — Inspect columns, dtypes, null counts, sample rows
3. run_data_query(code) — Execute Python/pandas code against loaded DataFrames
4. search_document(filename, query) — Search for text in PDF/Word/PPT files

Rules for run_data_query:
- DataFrame variable names come from list_loaded_files (e.g. `obesity_data`, not `obesity_data.csv`)
- Always use print() to output results — bare expressions are NOT shown
- For charts: assign a Plotly figure to a variable (e.g. `fig = px.bar(df, x='col', y='val')`)
- Available libraries: pd, np, px (plotly.express), go (plotly.graph_objects)
- For large datasets: ALWAYS use aggregation — .groupby(), .describe(), .value_counts(), .nlargest()
- NEVER print raw DataFrames with many rows — use head(10) at most
- One run_data_query call should be enough per sub-question; combine steps into one code block

Efficiency rules (important for large files):
- Call list_loaded_files ONCE at the start, not repeatedly
- Call get_file_details only if you need column specifics not already known
- Do ALL analysis in a single run_data_query block where possible
- After 2-3 tool calls you should have enough to write a final answer

ALWAYS end with a clear, structured answer in plain text — do not keep calling tools indefinitely."""


FINALIZE_PROMPT = (
    "You now have all the data you need. "
    "Stop calling tools and write your complete, structured final answer for the user right now. "
    "Summarise every finding clearly."
)


class DataChatAgent:
    def __init__(self, store: DataStore):
        self.store = store
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="list_loaded_files",
                    description="List all loaded files with variable names, shapes, and column names.",
                    parameters=types.Schema(type=types.Type.OBJECT, properties={}),
                ),
                types.FunctionDeclaration(
                    name="get_file_details",
                    description=(
                        "Return schema for a specific file: column names, data types, "
                        "null counts, and 3 sample rows. Use only if column names are unknown."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "filename": types.Schema(
                                type=types.Type.STRING,
                                description="Variable name or original filename",
                            ),
                        },
                        required=["filename"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="run_data_query",
                    description=(
                        "Execute Python/pandas/plotly code. "
                        "Use print() for output. Use aggregation for large datasets — never print raw rows. "
                        "Combine multiple analysis steps into ONE code block."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "code": types.Schema(
                                type=types.Type.STRING,
                                description="Python code to execute",
                            ),
                        },
                        required=["code"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="search_document",
                    description="Find relevant sections in a document (PDF, Word, PPT) by keyword.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "filename": types.Schema(type=types.Type.STRING, description="Document filename"),
                            "query": types.Schema(type=types.Type.STRING, description="Search keywords"),
                        },
                        required=["filename", "query"],
                    ),
                ),
            ])
        ]
        self._config_with_tools = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self._tools,
            temperature=0.1,
        )
        # Config with NO tools — forces a text-only final response
        self._config_final = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        )

    # ── Tool execution ─────────────────────────────────────────────────────────

    def _execute_tool(
        self, name: str, args: dict
    ) -> Tuple[str, Optional[go.Figure]]:

        if name == "list_loaded_files":
            return self.store.get_context_summary(), None

        if name == "get_file_details":
            fname = args.get("filename", "")
            fd = self.store.get_file(fname)
            if not fd:
                return f"File '{fname}' not found. Call list_loaded_files first.", None
            if fd.file_type == 'tabular':
                df = fd.dataframe
                # Cap column detail for very wide tables
                MAX_COLS = 30
                show_cols = list(df.columns[:MAX_COLS])
                col_lines = "\n".join(
                    f"  {col} ({df[col].dtype}) — {int(df[col].isna().sum())} nulls"
                    for col in show_cols
                )
                if len(df.columns) > MAX_COLS:
                    col_lines += f"\n  ... +{len(df.columns) - MAX_COLS} more columns (use run_data_query to inspect)"
                sample = df.head(3).to_string(max_cols=15)
                return (
                    f"**{fd.filename}** — {len(df):,} rows × {len(df.columns)} cols\n\n"
                    f"Columns (first {min(len(df.columns), MAX_COLS)}):\n{col_lines}\n\n"
                    f"Sample (3 rows):\n{sample}"
                ), None
            else:
                meta_str = json.dumps(fd.metadata, default=str, indent=2) if fd.metadata else "{}"
                result = f"**{fd.filename}** (document)\nMetadata:\n{meta_str}"
                if fd.tables:
                    result += f"\n\n{len(fd.tables)} embedded table(s) (first shown):\n{fd.tables[0].head(3).to_string()}"
                return result, None

        if name == "run_data_query":
            code = args.get("code", "")
            dfs = self.store.get_all_dataframes()
            output, figure = execute_data_code(code, dfs)
            return output, figure

        if name == "search_document":
            fname = args.get("filename", "")
            query = args.get("query", "")
            fd = self.store.get_file(fname)
            if not fd:
                return f"File '{fname}' not found.", None
            if not fd.text_content:
                return f"No text content in '{fname}'.", None
            words = query.lower().split()
            lines = [l for l in fd.text_content.split('\n') if l.strip()]
            scored = sorted(
                ((sum(1 for w in words if w in l.lower()), l) for l in lines),
                key=lambda x: -x[0],
            )
            hits = [line for score, line in scored if score > 0][:40]
            return ('\n'.join(hits) if hits else "No matching content found."), None

        return f"Unknown tool: {name}", None

    # ── Main chat loop ─────────────────────────────────────────────────────────

    async def chat(
        self, user_message: str, history: list
    ) -> AsyncGenerator:
        """
        Async generator. Yields:
          ('step',        tool_name, args_dict)
          ('step_result', tool_name, result_str)
          ('chart',       plotly_figure)
          ('final',       response_text)
          ('error',       error_message)
        """
        contents = list(history) + [
            types.Content(role='user', parts=[types.Part(text=user_message)])
        ]

        tool_turn_count = 0

        for turn in range(MAX_TURNS):
            # ── Force finalize: inject a "stop calling tools" message ──────────
            if tool_turn_count >= FORCE_FINALIZE_AT:
                contents.append(
                    types.Content(role='user', parts=[types.Part(text=FINALIZE_PROMPT)])
                )
                # Use config without tools so model CANNOT make more tool calls
                use_config = self._config_final
            else:
                use_config = self._config_with_tools

            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=use_config,
                )
            except Exception as exc:
                yield ('error', str(exc))
                return

            candidate = response.candidates[0]
            fn_calls = [
                p.function_call
                for p in candidate.content.parts
                if p.function_call
            ]

            # ── No tool calls → this is the final text response ────────────────
            if not fn_calls:
                text = ''.join(
                    p.text for p in candidate.content.parts if p.text
                )
                if text.strip():
                    yield ('final', text)
                else:
                    yield ('error', "Model returned an empty response.")
                return

            # ── Execute tool calls ─────────────────────────────────────────────
            tool_turn_count += 1
            contents.append(candidate.content)

            fn_response_parts = []
            for fc in fn_calls:
                args = dict(fc.args) if fc.args else {}
                yield ('step', fc.name, args)

                text_result, figure = self._execute_tool(fc.name, args)

                if figure is not None:
                    yield ('chart', figure)
                yield ('step_result', fc.name, text_result)

                # Cap tool result size sent back to the model
                capped = text_result[:6000]
                if len(text_result) > 6000:
                    capped += f"\n[Result capped at 6000 chars. {len(text_result)} total.]"

                fn_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": capped},
                        )
                    )
                )

            contents.append(
                types.Content(role='user', parts=fn_response_parts)
            )

        # Should never reach here — force-finalize kicks in before this
        yield ('error', "Exceeded maximum reasoning steps.")
