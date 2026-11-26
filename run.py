"""Fetch, validate and combine GB generation data, then write CSVs, a chart and a report.

Usage:  python run.py --start 2026-10-01 --end 2026-10-31
"""
import argparse
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.fetch import fetch_bmrs, fetch_pvlive
from src.process import (combine, monthly_energy_gwh, solar_share, tidy_bmrs,
                         tidy_pvlive, validate)

DATA, OUT = Path("data"), Path("outputs")


def main(start: date, end: date):
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    print(f"Fetching {start} to {end} ...")
    bmrs = tidy_bmrs(fetch_bmrs(start, end))
    solar = tidy_pvlive(fetch_pvlive(start, end))
    # keep only the requested UTC window in both sources
    lo, hi = bmrs["start_utc"].min(), bmrs["start_utc"].max()
    solar = solar[(solar["start_utc"] >= lo) & (solar["start_utc"] <= hi)]

    issues = validate(bmrs, "BMRS FUELHH", key=("start_utc", "fuel")) + validate(solar, "PV_Live")
    wide = combine(bmrs, solar)
    monthly = monthly_energy_gwh(wide)
    share = solar_share(wide)

    bmrs.to_csv(DATA / "bmrs_fuelhh.csv", index=False)
    solar.to_csv(DATA / "pvlive_solar.csv", index=False)
    wide.to_csv(DATA / "combined_halfhourly_mw.csv")
    monthly.to_csv(OUT / "monthly_gwh.csv")

    # chart: daily average generation by source, solar estimate on top
    daily = wide.resample("D").mean() / 1000  # GW
    ax = daily.plot.area(figsize=(11, 5.5), linewidth=0)
    ax.set_title(f"GB generation, daily average ({start} to {end})\n"
                 "BMRS transmission data has no solar: PV_Live estimate added on top")
    ax.set_ylabel("GW")
    ax.set_xlabel("")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / "generation_mix.png", dpi=150)

    report = [f"# Validation and reconciliation report ({start} to {end})", "",
              "## Data-quality checks",
              *(f"- {i}" for i in issues), *(["- No issues found"] if not issues else []), "",
              "## Solar share of domestic generation",
              f"- BMRS alone: {share['bmrs_only_pct']}% (no solar category in FUELHH)",
              f"- With PV_Live embedded solar estimate: {share['with_embedded_pct']}%",
              f"- BMRS domestic generation: {share['bmrs_total_gwh']} GWh; "
              f"solar estimate: {share['solar_gwh']} GWh", "",
              "## Monthly energy (GWh)", "", monthly.to_markdown(), "",
              "Next: reconcile monthly totals with DESNZ Energy Trends (see README roadmap)."]
    (OUT / "report.md").write_text("\n".join(report))
    print("\n".join(report))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    a = p.parse_args()
    main(a.start, a.end)
