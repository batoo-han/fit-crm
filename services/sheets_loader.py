"""Google Sheets loader for training programs (men/women 12-week).

Requires Service Account credentials file path from env GOOGLE_SHEETS_CREDENTIALS
and sheet IDs from env GOOGLE_SHEET_ID or direct URLs TRAINING_PLAN_WOMEN/MEN.
"""
from typing import List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
import re
import os


SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_client() -> gspread.Client:
    credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS is not set")
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPE)
    gc = gspread.authorize(creds)
    return gc


def _open_by_url_or_id(gc: gspread.Client, url_or_id: str):
    # Accept full URL or spreadsheet id
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)/", url_or_id)
    spreadsheet_id = match.group(1) if match else url_or_id
    return gc.open_by_key(spreadsheet_id)


def load_training_sheet(gender: str) -> List[Dict[str, Any]]:
    """Load the primary sheet (Men_12w_2 / Women_12w_2) as records.

    Returns list of dict rows with headers mapped.
    """
    gc = _get_client()
    if gender == "male":
        url = os.getenv("TRAINING_PLAN_MEN")
        sheet_name = "Men_12w_2"
    else:
        url = os.getenv("TRAINING_PLAN_WOMEN")
        sheet_name = "Women_12w_2"
    if not url:
        raise RuntimeError("Training plan URL is not configured in env")

    sh = _open_by_url_or_id(gc, url)
    ws = sh.worksheet(sheet_name)
    records = ws.get_all_records()
    return records


def normalize_age_group(age_group: str) -> range:
    # Examples: "17-25", "26-35", "45+"
    if not age_group:
        return range(0, 200)
    age_group = age_group.strip()
    if "+" in age_group:
        start = int(age_group.replace("+", "").strip())
        return range(start, 200)
    if "-" in age_group:
        a, b = age_group.split("-", 1)
        return range(int(a.strip()), int(b.strip()) + 1)
    # fallback
    try:
        v = int(age_group)
        return range(v, v + 1)
    except Exception:
        return range(0, 200)


