#!/usr/bin/env python3
"""Export public API-Sports football fixtures to a credential-free JSON feed."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://v3.football.api-sports.io/fixtures"
SETTLED_STATUS = {"FT", "AET", "PEN"}
LIVE_STATUS = {"1H", "HT", "2H", "ET", "BT", "P", "INT", "LIVE"}


def normalize_fixture(raw: dict) -> dict:
    """Keep only public display data; 1X2 always uses 90-minute full-time scores."""
    fixture = raw["fixture"]
    status = fixture["status"]["short"]
    fulltime = raw.get("score", {}).get("fulltime") or {}
    home_ft, away_ft = fulltime.get("home"), fulltime.get("away")
    settled = (
        status in SETTLED_STATUS
        and isinstance(home_ft, int)
        and isinstance(away_ft, int)
    )
    winner = (
        "HOME" if home_ft > away_ft else "AWAY" if away_ft > home_ft else "DRAW"
    ) if settled else None
    league = raw["league"]
    home, away = raw["teams"]["home"], raw["teams"]["away"]
    goals = raw.get("goals") or {}
    return {
        "id": fixture["id"],
        "kickoff_utc": datetime.fromtimestamp(fixture["timestamp"], timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "status_label": fixture["status"].get("long") or status,
        "elapsed_minutes": fixture["status"].get("elapsed"),
        "league": {"id": league["id"], "name": league["name"], "country": league["country"]},
        "home": {"id": home["id"], "name": home["name"]},
        "away": {"id": away["id"], "name": away["name"]},
        "display_score": {
            "home": goals.get("home") if status in LIVE_STATUS | SETTLED_STATUS else None,
            "away": goals.get("away") if status in LIVE_STATUS | SETTLED_STATUS else None,
        },
        "fulltime_score": {"home": home_ft, "away": away_ft} if settled else None,
        "winner_1x2": winner,
    }


def fetch_day(day: date, key: str) -> list[dict]:
    url = API_URL + "?" + urlencode({"date": day.isoformat()})
    request = Request(url, headers={"x-apisports-key": key})
    with urlopen(request, timeout=25) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError("API-Sports returned an error; no feed was written")
    fixtures = payload.get("response")
    if not isinstance(fixtures, list):
        raise RuntimeError("API-Sports response has no fixture list")
    return [normalize_fixture(item) for item in fixtures]


def export(day_from: date, day_to: date, output: Path, key: str) -> dict:
    if day_to < day_from or (day_to - day_from).days > 14:
        raise ValueError("date range must span 0..14 days")
    fixtures = []
    day = day_from
    while day <= day_to:
        fixtures.extend(fetch_day(day, key))
        day += timedelta(days=1)
    fixtures.sort(key=lambda item: (item["kickoff_utc"], item["id"]))
    payload = {
        "schema_version": 1,
        "source": "API-Sports Football v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "range": {"from": day_from.isoformat(), "to": day_to.isoformat()},
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, separators=(",", ":"))
        tmp.write("\n")
        temp_path = Path(tmp.name)
    temp_path.replace(output)
    return {"fixture_count": len(fixtures), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="day_from", type=date.fromisoformat, required=True)
    parser.add_argument("--to", dest="day_to", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    key = os.environ.get("API_SPORTS_KEY_2") or os.environ.get("API_SPORTS_KEY")
    if not key:
        parser.error("API_SPORTS_KEY_2 or API_SPORTS_KEY environment variable is required")
    print(json.dumps(export(args.day_from, args.day_to, args.output, key)))


if __name__ == "__main__":
    main()
