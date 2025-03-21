# config.py
"""Configuration constants and paths for the Streamlit application."""

from pathlib import Path

FRAME_LABELS = [
    "Pred:Bias",
    "Pred:FN",
    "Pred:FP",
    "Pred:Curve",
    "Pred:Occ",
    "Pred:Branch",
    "Pred:Merge",
    "GT:Bias",
    "GT:FN",
    "GT:FP",
    "GT:Elev",
    "GT:Incomp",
    "Normal",
]
"""List[str]: Available labels for frame classification."""

BASE_DIR = Path(__file__).parent
"""Path: Base directory of the project."""

LABEL_FILE_PATH = BASE_DIR / "data" / "labels.csv"
"""Path: File path for storing frame labels."""

ARTIFACTS_FOLDER = BASE_DIR / "artifacts"
"""Path: Directory for storing generated artifacts."""
