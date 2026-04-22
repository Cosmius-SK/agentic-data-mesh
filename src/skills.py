import pandas as pd
import plotly.express as px
import os

REPORT_DIR = "data/pulse_generated"

class SovereignSkills:
    @staticmethod
    async def skill_profiler(params):
        """Analyze file structure without loading full data."""
        filename = params.get("filename")
        df = pd.read_csv(f"data/{filename}", nrows=100)
        return f"File {filename} has {len(df.columns)} columns. Summary: {df.describe().to_json()}"

    @staticmethod
    async def skill_plotter(params):
        """Generates a Plotly chart and saves to pulse_generated."""
        df = pd.read_csv(f"data/{params['filename']}")
        fig = px.line(df, x=params['x'], y=params['y'], title=params['title'], template="plotly_dark")
        path = os.path.join(REPORT_DIR, f"{params['title']}.html")
        fig.write_html(path)
        return path
