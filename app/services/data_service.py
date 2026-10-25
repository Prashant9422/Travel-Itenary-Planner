from pathlib import Path
import re
import pandas as pd
from app.config import DATA_DIR

FILES = {"flights": "flights.csv", "hotels": "hotels.csv", "attractions": "attractions.csv", "guides": "destination_guides.csv"}


def display_source_name(source: str) -> str:
    source_names = {
        "attractions.csv": "Attractions data",
        "hotels.csv": "Accommodation data",
        "flights.csv": "Flight data",
        "destination_guides.csv": "Destination guidance",
        "travel_basics.md": "General travel guidance",
    }
    if source in source_names:
        return source_names[source]

    return re.sub(
        r"\b([A-Za-z0-9_-]+)\.(?:csv|md)\b",
        lambda match: source_names.get(match.group(0), match.group(1).replace("_", " ").title()),
        source,
        flags=re.IGNORECASE,
    )


def load_csv(name: str) -> pd.DataFrame:
    if name not in FILES:
        raise ValueError(f"Unknown data set: {name}")
    path = DATA_DIR / FILES[name]
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def is_synthetic_record(row: pd.Series) -> bool:
    markers = f"{row.get('source', '')} {row.get('notes', '')}".casefold()
    return any(marker in markers for marker in ("synthetic", "test fixture", "not a real place"))


def destination_rows(name: str, destination: str) -> pd.DataFrame:
    df = load_csv(name)
    if df.empty or "destination" not in df.columns:
        return df
    destinations = df["destination"].astype(str).str.strip()
    requested_parts = {
        part.strip().casefold()
        for part in destination.split(",")
        if part.strip()
    }
    matching = destinations.str.casefold().isin(requested_parts)
    if matching.any():
        return df[matching]
    return df[destinations.str.contains(destination, case=False, regex=False)]

def format_context(destination: str, origin: str = "") -> str:
    sections = []
    for name in ("attractions", "hotels", "flights", "guides"):
        df = destination_rows(name, destination)
        if not df.empty and {"source", "notes"}.intersection(df.columns):
            df = df[~df.apply(is_synthetic_record, axis=1)]
        if name == "flights" and origin.strip():
            df = df[df["origin"].astype(str).str.casefold().isin({
                part.strip().casefold()
                for part in origin.split(",")
                if part.strip()
            })] if not df.empty and "origin" in df.columns else df.iloc[0:0]
        if not df.empty:
            sections.append(f"{name.upper()} DATA:\n{df.head(12).to_csv(index=False)}")
    return "\n\n".join(sections) or "No matching local data found. Do not invent live prices or availability."
