import os
import re
import pickle
import pandas as pd
from typing import Dict, Optional

from file_processor import FileData

UPLOAD_DIR = "data/uploads"


def _safe_var(name: str) -> str:
    """Convert a filename to a safe Python variable name."""
    base = os.path.splitext(name)[0]
    safe = re.sub(r'[^a-zA-Z0-9]', '_', base).strip('_')
    if not safe or safe[0].isdigit():
        safe = 'df_' + safe
    return safe or 'df'


class DataStore:
    def __init__(self):
        self.files: Dict[str, FileData] = {}
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        self._load_persisted()

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_file(self, fd: FileData, raw_bytes: bytes = None) -> None:
        self.files[fd.filename] = fd
        with open(os.path.join(UPLOAD_DIR, f"{fd.filename}.pkl"), 'wb') as f:
            pickle.dump(fd, f)
        if raw_bytes:
            with open(os.path.join(UPLOAD_DIR, fd.filename), 'wb') as f:
                f.write(raw_bytes)

    def get_file(self, name: str) -> Optional[FileData]:
        """Look up by original filename or safe variable name."""
        if name in self.files:
            return self.files[name]
        for fname, fd in self.files.items():
            if _safe_var(fname) == name:
                return fd
        return None

    def list_files(self) -> list:
        return list(self.files.keys())

    def get_all_dataframes(self) -> Dict[str, pd.DataFrame]:
        """Return {safe_var_name: DataFrame} for all tabular files."""
        result: Dict[str, pd.DataFrame] = {}
        for name, fd in self.files.items():
            if fd.file_type != 'tabular':
                continue
            var = _safe_var(name)
            result[var] = fd.dataframe
            if fd.dataframes and len(fd.dataframes) > 1:
                for sheet, df in fd.dataframes.items():
                    result[f"{var}_{_safe_var(sheet)}"] = df
        return result

    def get_context_summary(self) -> str:
        if not self.files:
            return "No files loaded."
        lines = ["**Loaded files:**"]
        for name, fd in self.files.items():
            var = _safe_var(name)
            if fd.file_type == 'tabular':
                df = fd.dataframe
                cols = ', '.join(f'`{c}`' for c in df.columns[:8])
                if len(df.columns) > 8:
                    cols += f' … +{len(df.columns) - 8} more'
                line = (
                    f"- **{name}** (var: `{var}`) — "
                    f"{len(df):,} rows × {len(df.columns)} cols\n  Columns: {cols}"
                )
                if fd.sheet_names and len(fd.sheet_names) > 1:
                    line += f"\n  Sheets: {', '.join(fd.sheet_names)}"
                lines.append(line)
            elif fd.slides:
                lines.append(f"- **{name}** — {fd.metadata['slide_count']} slides (PPT)")
            elif fd.metadata and 'page_count' in fd.metadata:
                extra = f", {len(fd.tables)} table(s)" if fd.tables else ""
                lines.append(f"- **{name}** — {fd.metadata['page_count']} pages{extra} (PDF)")
            else:
                wc = fd.metadata.get('word_count', '?') if fd.metadata else '?'
                extra = f", {len(fd.tables)} table(s)" if fd.tables else ""
                lines.append(f"- **{name}** — ~{wc} words{extra} (Word)")
        return '\n'.join(lines)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_persisted(self) -> None:
        for fname in os.listdir(UPLOAD_DIR):
            if not fname.endswith('.pkl'):
                continue
            try:
                with open(os.path.join(UPLOAD_DIR, fname), 'rb') as f:
                    fd: FileData = pickle.load(f)
                self.files[fd.filename] = fd
            except Exception:
                pass
