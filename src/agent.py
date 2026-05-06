import os
import asyncio
import json
from typing import AsyncGenerator, Dict, Optional, Tuple

import plotly.graph_objects as go
from google import genai
from google.genai import types

from data_store import DataStore, _safe_var
from code_executor import execute_data_code


SYSTEM_PROMPT = """You are a Data Analysis Assistant. Users upload files (CSV, Excel, PDF, Word, PPT) and you answer questions about them.

You have these tools:
1. list_loaded_files — See all loaded files, variable names, and structure
2. get_file_details(filename) — Inspect columns, dtypes, null counts, 5 sample rows
3. run_data_query(code) — Execute Python/pandas code against loaded DataFrames
4. search_document(filename, query) — Search for text in PDF/Word/PPT files

Rules for run_data_query:
- DataFrame variable names come from list_loaded_files (e.g. `sales_data`, not `sales_data.csv`)
- Always use print() to output results — bare expressions are NOT shown
- For charts: assign a Plotly figure to any variable (e.g. `fig = px.bar(df, x='col', y='val')`)
- For multi-sheet Excel: variables are `{file}_{sheet}` (e.g. `report_Q1`, `report_Q2`)
- You can merge DataFrames across files with pd.merge() if they share a column
- Available libraries: pd, np, px (plotly.express), go (plotly.graph_objects)

Always call list_loaded_files first if you are unsure what data is available.
Be precise and show your working. When answering from documents, quote relevant sections."""


class DataChatAgent:
    def __init__(self, store: DataStore):
        self.store = store
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="list_loaded_files",
                    description="List all loaded files with their variable names, shapes, and column names.",
                    parameters=types.Schema(type=types.Type.OBJECT, properties={}),
                ),
                types.FunctionDeclaration(
                    name="get_file_details",
                    description=(
                        "Return detailed info for a specific file: all column names, data types, "
                        "null counts, and the first 5 rows."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "filename": types.Schema(
                                type=types.Type.STRING,
                                description="Variable name (e.g. sales_data) or original filename",
                            ),
                        },
                        required=["filename"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="run_data_query",
                    description=(
                        "Execute Python/pandas/plotly code against the loaded DataFrames. "
                        "Use print() for text output. Assign Plotly figures to a variable for charts."
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
                    description=(
                        "Find relevant paragraphs or sections in a document file (PDF, Word, PPT) "
                        "matching the query keywords."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "filename": types.Schema(
                                type=types.Type.STRING,
                                description="Original filename of the document",
                            ),
                            "query": types.Schema(
                                type=types.Type.STRING,
                                description="Keywords or question to search for",
                            ),
                        },
                        required=["filename", "query"],
                    ),
                ),
            ])
        ]

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
                return f"File '{fname}' not found. Call list_loaded_files to see available files.", None
            if fd.file_type == 'tabular':
                df = fd.dataframe
                col_lines = "\n".join(
                    f"  {col} ({df[col].dtype}) — {df[col].isna().sum()} nulls"
                    for col in df.columns
                )
                sample = df.head(5).to_string()
                return (
                    f"**{fd.filename}** — {len(df):,} rows × {len(df.columns)} cols\n\n"
                    f"Columns:\n{col_lines}\n\nSample (5 rows):\n{sample}"
                ), None
            else:
                meta_str = json.dumps(fd.metadata, default=str, indent=2) if fd.metadata else "{}"
                result = f"**{fd.filename}** (document)\nMetadata:\n{meta_str}"
                if fd.tables:
                    result += f"\n\n{len(fd.tables)} embedded table(s):"
                    for i, tbl in enumerate(fd.tables[:3], 1):
                        result += f"\n\nTable {i}:\n{tbl.head(4).to_string()}"
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
            hits = [line for score, line in scored if score > 0][:50]
            return ('\n'.join(hits) if hits else "No matching content found."), None

        return f"Unknown tool: {name}", None

    # ── Main chat loop ─────────────────────────────────────────────────────────

    async def chat(
        self, user_message: str, history: list
    ) -> AsyncGenerator:
        """
        Async generator. Yields tuples:
          ('step',        tool_name, args_dict)
          ('step_result', tool_name, result_str)
          ('chart',       plotly_figure)
          ('final',       response_text)
          ('error',       error_message)
        """
        contents = list(history) + [
            types.Content(role='user', parts=[types.Part(text=user_message)])
        ]
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self._tools,
            temperature=0.1,
        )

        for _ in range(10):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config,
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

            if not fn_calls:
                text = ''.join(
                    p.text for p in candidate.content.parts if p.text
                )
                yield ('final', text)
                return

            # Append model's tool-call turn to history
            contents.append(candidate.content)

            # Execute each tool call and collect responses
            fn_response_parts = []
            for fc in fn_calls:
                args = dict(fc.args) if fc.args else {}
                yield ('step', fc.name, args)

                text_result, figure = self._execute_tool(fc.name, args)

                if figure is not None:
                    yield ('chart', figure)
                yield ('step_result', fc.name, text_result)

                fn_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": text_result[:12000]},
                        )
                    )
                )

            # Return tool results to the model
            contents.append(
                types.Content(role='user', parts=fn_response_parts)
            )

        yield ('error', "Reached maximum reasoning steps without a final answer.")
