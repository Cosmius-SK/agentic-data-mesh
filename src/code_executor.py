import io
import traceback
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Tuple, Optional


_SAFE_BUILTINS = {
    'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,
    'map': map, 'filter': filter, 'list': list, 'dict': dict, 'set': set,
    'tuple': tuple, 'str': str, 'int': int, 'float': float, 'bool': bool,
    'round': round, 'sum': sum, 'min': min, 'max': max, 'abs': abs,
    'sorted': sorted, 'reversed': reversed, 'type': type,
    'isinstance': isinstance, 'hasattr': hasattr, 'getattr': getattr,
    'any': any, 'all': all, 'repr': repr, 'format': format,
    'True': True, 'False': False, 'None': None,
}

# Hard cap on printed output sent back to the LLM.
# Large datasets can print millions of characters — that confuses the model.
_MAX_OUTPUT_CHARS = 4000
_MAX_OUTPUT_LINES = 60


def execute_data_code(
    code: str,
    dataframes: Dict[str, pd.DataFrame],
) -> Tuple[str, Optional[go.Figure]]:
    """
    Run pandas/plotly code in a restricted namespace.
    Returns (text_output, plotly_figure_or_None).
    """
    buf = io.StringIO()
    builtins = dict(_SAFE_BUILTINS)
    builtins['print'] = lambda *a, **kw: buf.write(
        ' '.join(str(x) for x in a) + kw.get('end', '\n')
    )

    namespace: dict = {
        '__builtins__': builtins,
        'pd': pd,
        'np': np,
        'px': px,
        'go': go,
        **dataframes,
    }

    try:
        exec(compile(code, '<data_query>', 'exec'), namespace)
    except Exception:
        return f"```\n{traceback.format_exc()}\n```", None

    raw_output = buf.getvalue().strip()
    output = _truncate_output(raw_output)

    # Find first plotly Figure created in the namespace
    figure: Optional[go.Figure] = next(
        (
            v for k, v in namespace.items()
            if not k.startswith('_')
            and k not in ('pd', 'np', 'px', 'go')
            and isinstance(v, go.Figure)
        ),
        None,
    )

    if not output and figure is None:
        output = "Code executed (no printed output)."

    return output, figure


def _truncate_output(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    if len(lines) > _MAX_OUTPUT_LINES:
        kept = '\n'.join(lines[:_MAX_OUTPUT_LINES])
        note = (
            f"\n\n[Output truncated: showed {_MAX_OUTPUT_LINES} of {len(lines)} lines. "
            "Use aggregation (.groupby, .describe, .value_counts) to summarise large results.]"
        )
        return kept + note
    if len(text) > _MAX_OUTPUT_CHARS:
        note = (
            f"\n\n[Output truncated at {_MAX_OUTPUT_CHARS} chars. "
            "Use .head(), .describe(), or aggregation for concise results.]"
        )
        return text[:_MAX_OUTPUT_CHARS] + note
    return text
