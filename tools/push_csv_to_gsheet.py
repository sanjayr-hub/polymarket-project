import os
import csv
import json
import argparse
import gspread
from google.oauth2.service_account import Credentials

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV file to upload")
    parser.add_argument("--sheet_id", required=True, help="Google Sheet spreadsheet ID")
    parser.add_argument("--tab", required=True, help="Worksheet/tab name")
    args = parser.parse_args()

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise RuntimeError("Missing env var GOOGLE_SERVICE_ACCOUNT_JSON")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=scopes)
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(args.sheet_id)
    ws = sh.worksheet(args.tab)

    # Read CSV into a 2D array
    with open(args.csv, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise RuntimeError("CSV appears empty")

    # Clear then write (simple + reliable)
    ws.clear()
    ws.update(values=rows, range_name="A1")

    print(f"Uploaded {len(rows)-1} data rows (+ header) to {args.sheet_id}/{args.tab}")

if __name__ == "__main__":
    main()
