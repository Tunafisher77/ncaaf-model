"""Google Sheets helpers for the NCAAF weekly model."""

from __future__ import annotations

import json
import os
import re

import google.auth
import gspread
from google.oauth2.service_account import Credentials


def normalize_spreadsheet_id_(value: str) -> str:
    """Accept either a bare spreadsheet ID or a full Google Sheets URL."""
    value = value.strip().strip("'\"")
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", value)
    if match:
        return match.group(1)
    return value.split("?", 1)[0].split("#", 1)[0].removesuffix("/edit").strip("/")


def open_google_book_():
    spreadsheet_id = normalize_spreadsheet_id_(os.getenv("GOOGLE_SHEETS_ID", ""))
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_ID is required.")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    raw_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_credentials:
        credentials = Credentials.from_service_account_info(json.loads(raw_credentials), scopes=scopes)
    else:
        credentials, _ = google.auth.default(scopes=scopes)
    return gspread.authorize(credentials).open_by_key(spreadsheet_id)


def rows_to_sheet(tab_name: str, rows: list[list[object]]) -> None:
    book = open_google_book_()
    try:
        sheet = book.worksheet(tab_name)
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = book.add_worksheet(title=tab_name, rows=max(200, len(rows) + 20), cols=12)
    sheet.update(rows, value_input_option="RAW")


def read_records_sheet(tab_name: str) -> list[dict]:
    book = open_google_book_()
    try:
        return book.worksheet(tab_name).get_all_records()
    except gspread.WorksheetNotFound:
        return []


def upsert_records_sheet(tab_name: str, records: list[dict], key_fields: tuple[str, ...]) -> None:
    if not records:
        return
    book = open_google_book_()
    try:
        sheet = book.worksheet(tab_name)
        existing = sheet.get_all_records()
    except gspread.WorksheetNotFound:
        sheet = book.add_worksheet(title=tab_name, rows=500, cols=max(12, len(records[0])))
        existing = []
    incoming_keys = {tuple(str(row.get(key, "")) for key in key_fields) for row in records}
    retained = [row for row in existing if tuple(str(row.get(key, "")) for key in key_fields) not in incoming_keys]
    combined = retained + records
    headers = list(records[0].keys())
    for row in retained:
        for key in row:
            if key not in headers:
                headers.append(key)
    sheet.clear()
    sheet.update([headers] + [[row.get(header, "") for header in headers] for row in combined], value_input_option="RAW")
