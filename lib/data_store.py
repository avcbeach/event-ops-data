import io
import pandas as pd
from lib.github_store import github_read_text, github_write_text

def ensure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Ensure dataframe has all required columns.
    Missing ones are created with empty string.
    This makes old CSVs backward-compatible forever.
    """
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df

def read_csv(path: str, columns: list[str]) -> pd.DataFrame:
    txt, _ = github_read_text(path)
    if txt.strip():
        df = pd.read_csv(io.StringIO(txt), dtype=str).fillna("")
    else:
        df = pd.DataFrame()

    df = ensure_cols(df, columns)
    return df

def write_csv(path: str, df: pd.DataFrame, message: str):
    csv_text = df.to_csv(index=False)
    github_write_text(path, csv_text, message)
