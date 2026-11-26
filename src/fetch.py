"""Download raw data from public APIs (no API keys needed).

- Elexon BMRS FUELHH: half-hourly generation by fuel type, transmission-connected only.
- Sheffield Solar PV_Live: half-hourly estimate of total GB solar generation
  (mostly embedded in distribution networks, so missing from BMRS).
"""
from datetime import date, timedelta

import pandas as pd
import requests

BMRS_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH"
PVLIVE_URL = "https://api.pvlive.uk/pvlive/api/v4/gsp/0"  # GSP 0 = national total
CHUNK_DAYS = 7  # keep each request small and polite


def _chunks(start: date, end: date, days: int = CHUNK_DAYS):
    """Yield (chunk_start, chunk_end) pairs covering start..end inclusive."""
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def fetch_bmrs(start: date, end: date, session=None) -> pd.DataFrame:
    """Return raw FUELHH rows for settlement dates start..end (inclusive)."""
    s = session or requests.Session()
    frames = []
    for a, b in _chunks(start, end):
        r = s.get(BMRS_URL, params={"settlementDateFrom": a.isoformat(),
                                    "settlementDateTo": b.isoformat(),
                                    "format": "json"}, timeout=60)
        r.raise_for_status()
        frames.append(pd.DataFrame(r.json()["data"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fetch_pvlive(start: date, end: date, session=None) -> pd.DataFrame:
    """Return PV_Live national solar estimates covering start..end (UTC days)."""
    s = session or requests.Session()
    frames = []
    for a, b in _chunks(start, end):
        r = s.get(PVLIVE_URL, params={"start": f"{a.isoformat()}T00:00:00Z",
                                      "end": f"{(b + timedelta(days=1)).isoformat()}T00:00:00Z",
                                      "data_format": "json"}, timeout=60)
        r.raise_for_status()
        j = r.json()
        frames.append(pd.DataFrame(j["data"], columns=j["meta"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
