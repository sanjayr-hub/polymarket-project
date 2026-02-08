#!/usr/bin/env python3
import csv
import os
import sys
import json
import ast
from datetime import datetime, timezone
from typing import Dict, Any, List

import requests
import yaml

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

OUT_FIELDS = [
    "ts_utc",
    "market_name",
    "market_slug",
    "market_id",
    "yes_token_id",
    "no_token_id",
    "yes_price",
    "no_price",
    "volume",
    "liquidity",
]

def coerce_list(x):
    """Coerce Gamma list-like fields which may arrive as JSON strings into Python lists."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return []
        try:
            v = json.loads(s)
            return v if isinstance(v, list) else [v]
        except Exception:
            pass
        try:
            v = ast.literal_eval(s)
            return v if isinstance(v, list) else [v]
        except Exception:
            return []
    return []

def get_market_by_slug(slug: str) -> Dict[str, Any]:
    url = f"{GAMMA_BASE}/markets/slug/{slug}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_price(token_id: str, side: str = "buy") -> float:
    url = f"{CLOB_BASE}/price"
    r = requests.get(url, params={"token_id": token_id, "side": side}, timeout=20)
    r.raise_for_status()
    return float(r.json()["price"])

def ensure_parent_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

def append_row(csv_path: str, row: Dict[str, Any]) -> None:
    ensure_parent_dir(csv_path)
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)

def write_latest(latest_path: str, rows: List[Dict[str, Any]]) -> None:
    ensure_parent_dir(latest_path)
    with open(latest_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow(row)

def load_config(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return [m for m in cfg.get("markets", []) if m.get("enabled", True)]

def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: polymarket_snapshot.py <config_yaml> <snapshots_csv> <latest_csv>")
        return 2

    config_path, snapshots_csv, latest_csv = sys.argv[1:4]
    markets = load_config(config_path)

    ts_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    latest_rows: List[Dict[str, Any]] = []

    for m in markets:
        name = m.get("name", "")
        slug = m["slug"]

        try:
            market = get_market_by_slug(slug)

            market_id = market.get("id", "")
            volume = market.get("volume", "")
            liquidity = market.get("liquidity", "")

            token_ids = coerce_list(market.get("clobTokenIds"))
            if len(token_ids) < 2:
                raise ValueError(f"Expected 2 clobTokenIds, got: {token_ids}")

            outcomes = coerce_list(market.get("outcomes"))

            yes_token_id = None
            no_token_id = None

            if outcomes and len(outcomes) == len(token_ids):
                for outcome, tid in zip(outcomes, token_ids):
                    o = str(outcome).strip().lower()
                    if o == "yes":
                        yes_token_id = str(tid)
                    elif o == "no":
                        no_token_id = str(tid)

            if not yes_token_id or not no_token_id:
                yes_token_id, no_token_id = str(token_ids[0]), str(token_ids[1])

            yes_price = get_price(yes_token_id, side="buy")
            no_price = get_price(no_token_id, side="buy")

            row = {
                "ts_utc": ts_utc,
                "market_name": name,
                "market_slug": slug,
                "market_id": market_id,
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "yes_price": yes_price,
                "no_price": no_price,
                "volume": volume,
                "liquidity": liquidity,
            }

            append_row(snapshots_csv, row)
            latest_rows.append(row)

        except Exception as e:
            print(f"[ERROR] slug={slug}: {e}", file=sys.stderr)

    if latest_rows:
        write_latest(latest_csv, latest_rows)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY
