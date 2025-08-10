#!/usr/bin/env python3
"""
Seed Square Sandbox with many paid orders for load testing and onboarding flows.

Usage examples:
  # Seed 1000 orders across all locations using env SQUARE_ACCESS_TOKEN
  python backend/scripts/seed_square_orders.py --count 1000

  # Seed 500 orders only into specified locations, ~60 orders/min, random amounts $8.99-$19.99
  python backend/scripts/seed_square_orders.py --count 500 \
      --location-ids LOC1,LOC2 --min-amount 899 --max-amount 1999 --rate 60

Environment:
  - SQUARE_ACCESS_TOKEN (preferred) or SQUARE_SANDBOX_ACCESS_TOKEN
  - Optional: FRONTEND_URL (not required here)

Notes:
  - This script uses the Square Sandbox API (squareupsandbox.com).
  - Orders are created and immediately paid using CASH payments (no card nonce required).
  - Keep an eye on rate limits. Use --rate to throttle requests per minute.
"""

import argparse
import json
import os
import random
import sys
import time
import uuid
from typing import List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv  # type: ignore
    from pathlib import Path
    # Load env from current working directory if present
    load_dotenv()
    # Also try backend/.env relative to this script
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir.parent / ".env")
except Exception:
    # It's okay if python-dotenv isn't installed; env can still come from the shell
    pass

BASE = "https://connect.squareupsandbox.com"


def get_access_token() -> str:
    token = os.getenv("SQUARE_ACCESS_TOKEN") or os.getenv("SQUARE_SANDBOX_ACCESS_TOKEN")
    if not token:
        print("ERROR: Missing SQUARE_ACCESS_TOKEN (or SQUARE_SANDBOX_ACCESS_TOKEN). Pass --token or set it in your env (backend/.env).", file=sys.stderr)
        sys.exit(2)
    return token


def auth_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_locations(token: str) -> List[dict]:
    url = f"{BASE}/v2/locations"
    r = requests.get(url, headers=auth_headers(token), timeout=20)
    try:
        r.raise_for_status()
    except Exception:
        print(f"Failed to fetch locations: {r.status_code} {r.text}", file=sys.stderr)
        raise
    data = r.json()
    return data.get("locations", [])


def choose_location_ids(all_locations: List[dict], filter_ids: Optional[List[str]]) -> List[str]:
    all_ids = [loc["id"] for loc in all_locations]
    if filter_ids:
        invalid = [lid for lid in filter_ids if lid not in all_ids]
        if invalid:
            print(f"WARNING: Some provided --location-ids are not in your account and will be ignored: {invalid}")
        return [lid for lid in filter_ids if lid in all_ids]
    return all_ids


def build_random_line_items() -> List[dict]:
    # 1-3 items per order
    items = []
    num_items = random.randint(1, 3)
    menu = [
        ("Burger", [899, 1099, 1299]),
        ("Fries", [299, 399, 499]),
        ("Soda", [199, 249, 299]),
        ("Salad", [699, 899, 1099]),
        ("Pizza Slice", [399, 499, 599]),
    ]
    for _ in range(num_items):
        name, price_options = random.choice(menu)
        price = random.choice(price_options)
        qty = str(random.randint(1, 2))
        items.append({
            "name": name,
            "quantity": qty,
            "base_price_money": {"amount": price, "currency": "USD"}
        })
    return items


def create_order(token: str, location_id: str, override_amount_cents: Optional[int] = None) -> Tuple[str, int]:
    url = f"{BASE}/v2/orders"
    line_items = build_random_line_items()

    if override_amount_cents is not None:
        # Replace all item amounts with a single line that matches override
        line_items = [{
            "name": "Seed Item",
            "quantity": "1",
            "base_price_money": {"amount": override_amount_cents, "currency": "USD"}
        }]

    body = {
        "idempotency_key": str(uuid.uuid4()),
        "order": {
            "location_id": location_id,
            "line_items": line_items
        }
    }

    r = requests.post(url, headers=auth_headers(token), json=body, timeout=20)
    try:
        r.raise_for_status()
    except Exception:
        print(f"Failed to create order: {r.status_code} {r.text}", file=sys.stderr)
        raise
    data = r.json()
    order = data.get("order", {})

    # Prefer server-calculated total; fallback to sum
    amount = 0
    if order.get("total_money"):
        amount = int(order["total_money"].get("amount", 0))
    else:
        for li in line_items:
            amount += int(li["base_price_money"]["amount"]) * int(li["quantity"])  # type: ignore

    return order["id"], amount


def pay_order_cash(token: str, order_id: str, location_id: str, amount_cents: int) -> None:
    url = f"{BASE}/v2/payments"
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "source_id": "CASH",
        "amount_money": {"amount": amount_cents, "currency": "USD"},
        "location_id": location_id,
        "order_id": order_id,
        "cash_details": {"buyer_supplied_money": {"amount": amount_cents, "currency": "USD"}},
        "autocomplete": True
    }
    r = requests.post(url, headers=auth_headers(token), json=body, timeout=20)
    try:
        r.raise_for_status()
    except Exception:
        print(f"Failed to pay order {order_id}: {r.status_code} {r.text}", file=sys.stderr)
        raise


def backoff_sleep(attempt: int):
    # Exponential backoff up to ~5s
    time.sleep(min(5, 0.25 * (2 ** attempt)))


def seed_orders(token: str, count: int, location_ids: List[str], min_amount: Optional[int], max_amount: Optional[int], rate: int, dry_run: bool):
    if not location_ids:
        print("ERROR: No valid location IDs available.", file=sys.stderr)
        sys.exit(3)

    per_minute = max(1, rate)
    per_second = per_minute / 60.0
    interval = 1.0 / per_second
    next_time = time.time()

    successes = 0
    failures = 0

    for i in range(1, count + 1):
        loc = random.choice(location_ids)

        override_amount = None
        if min_amount is not None and max_amount is not None:
            override_amount = random.randint(min_amount, max_amount)

        # Throttle
        now = time.time()
        if now < next_time:
            time.sleep(next_time - now)
        next_time = max(next_time + interval, time.time())

        try:
            if dry_run:
                print(f"[DRY-RUN] Would create & pay order at location {loc} amount={override_amount if override_amount else 'random from items'}")
                successes += 1
                continue

            # Retry loop for transient errors (e.g., 429)
            attempt = 0
            while True:
                try:
                    order_id, amount = create_order(token, loc, override_amount)
                    pay_order_cash(token, order_id, loc, amount)
                    break
                except requests.HTTPError as http_err:
                    status = getattr(http_err.response, 'status_code', None)
                    if status in (429, 500, 502, 503, 504) and attempt < 5:
                        attempt += 1
                        print(f"Transient error {status}. Backing off (attempt {attempt})...")
                        backoff_sleep(attempt)
                        continue
                    raise

            successes += 1
            if i % 20 == 0 or i == count:
                print(f"Seeded {i}/{count} orders. Success={successes} Failures={failures}")

        except Exception as e:
            failures += 1
            print(f"ERROR seeding order {i}/{count} at location {loc}: {e}")

    print(f"Done. Total seeded: {successes}. Failures: {failures}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Square Sandbox orders")
    p.add_argument("--count", type=int, default=200, help="Total number of orders to create")
    p.add_argument("--location-ids", type=str, default=None, help="Comma-separated list of location IDs to target. Defaults to all sandbox locations")
    p.add_argument("--min-amount", type=int, default=None, help="Optional min amount (cents). If set with --max-amount, overrides line item pricing")
    p.add_argument("--max-amount", type=int, default=None, help="Optional max amount (cents). If set with --min-amount, overrides line item pricing")
    p.add_argument("--rate", type=int, default=120, help="Requests per minute (approx). Includes order+payment pair")
    p.add_argument("--dry-run", action="store_true", help="Do not call APIs; print what would happen")
    p.add_argument("--token", type=str, default=None, help="Square sandbox access token (overrides env)")
    p.add_argument("--env-file", type=str, default=None, help="Path to a .env file to load (e.g., Adaptiv/backend/.env)")
    return p.parse_args()


def main():
    args = parse_args()

    # Optionally load an explicit env file
    if args.env_file:
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(args.env_file, override=True)
        except Exception:
            pass

    token = args.token or get_access_token()

    try:
        locs = get_locations(token)
    except Exception as e:
        print("Failed to fetch locations. Ensure your token is a SANDBOX access token for the selected test account (Developer Dashboard > Sandbox > Access token).", file=sys.stderr)
        sys.exit(1)

    selected_location_ids = choose_location_ids(locs, args.location_ids.split(',') if args.location_ids else None)

    print(f"Found {len(locs)} locations. Using {len(selected_location_ids)} locations: {selected_location_ids}")
    if args.min_amount is not None and args.max_amount is not None and args.min_amount > args.max_amount:
        print("ERROR: --min-amount cannot be greater than --max-amount", file=sys.stderr)
        sys.exit(2)

    seed_orders(
        token=token,
        count=args.count,
        location_ids=selected_location_ids,
        min_amount=args.min_amount,
        max_amount=args.max_amount,
        rate=args.rate,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
