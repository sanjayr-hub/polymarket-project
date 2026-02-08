#!/usr/bin/env python3
import argparse
import csv
import json
import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_gspread_client():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise RuntimeError("Missing env var GOOGLE_SERVICE_ACCOUNT_JSON")

    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def read_csv(csv_path: str):
    with open(csv_path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    header = rows[0]
    data = rows[1:]
    return header, data

def get_or_create_worksheet(sh, tab_name: str, cols_hint: int = 26):
    try:
        return sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        # create with a reasonable default size
        return sh.add_worksheet(title=tab_name, rows=2000, cols=max(cols_hint, 26))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--sheet_id", required=True)
    p.add_argument("--tab", required=True)
    p.add_argument("--mode", choices=["replace", "append"], default="replace")
    args = p.parse_args()

    header, data = read_csv(args.csv)
    if not header:
        print("CSV is empty; nothing to write.")
        return 0

    gc = get_gspread_client()
    sh = gc.open_by_key(args.sheet_id)
    ws = get_or_create_worksheet(sh, args.tab, cols_hint=len(header))

    if args.mode == "replace":
        ws.clear()
        ws.update([header] + data)
        print(f"Replaced tab '{args.tab}' with {len(data)} rows (+ header).")
        return 0

    # append mode
    existing = ws.get_all_values()
    if not existing:
        ws.append_row(header)
        print(f"Wrote header to empty tab '{args.tab}'.")

    if data:
        ws.append_rows(data, value_input_option="RAW")
        print(f"Appended {len(data)} rows to '{args.tab}'.")
    else:
        print("No data rows to append.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
