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

    output = buf.getvalue().strip()

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
