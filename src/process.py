"""Clean, validate and combine BMRS and PV_Live data.

Every timestamp is the START of a half-hour period, in UTC.
Power values are MW (average over the half hour); energy = MW x 0.5 h = MWh.
"""
import pandas as pd

HALF_HOUR = pd.Timedelta(minutes=30)

# BMRS fuel codes -> readable groups. INT* are interconnector imports and PS is
# pumped storage: both are excluded from domestic generation (see METHODS.md).
FUEL_GROUPS = {
    "CCGT": "Gas", "OCGT": "Gas", "COAL": "Coal", "OIL": "Oil",
    "NUCLEAR": "Nuclear", "WIND": "Wind (transmission)", "BIOMASS": "Biomass",
    "NPSHYD": "Hydro", "OTHER": "Other", "PS": "Pumped storage",
}


def tidy_bmrs(raw: pd.DataFrame) -> pd.DataFrame:
    """Long table: start_utc, fuel, group, mw. Interconnectors kept but flagged."""
    df = raw[["startTime", "fuelType", "generation"]].copy()
    df.columns = ["start_utc", "fuel", "mw"]
    df["start_utc"] = pd.to_datetime(df["start_utc"], utc=True)
    df["group"] = df["fuel"].map(FUEL_GROUPS).fillna(
        df["fuel"].where(~df["fuel"].str.startswith("INT"), "Interconnector imports"))
    return df.drop_duplicates(["start_utc", "fuel"]).sort_values(["start_utc", "fuel"])


def tidy_pvlive(raw: pd.DataFrame) -> pd.DataFrame:
    """PV_Live labels each value by the period END; shift to period START."""
    df = raw[["datetime_gmt", "generation_mw"]].copy()
    df.columns = ["end_utc", "mw"]
    df["start_utc"] = pd.to_datetime(df["end_utc"], utc=True) - HALF_HOUR
    return (df[["start_utc", "mw"]].drop_duplicates("start_utc")
            .sort_values("start_utc").reset_index(drop=True))


def validate(df: pd.DataFrame, name: str, key=("start_utc",)) -> list[str]:
    """Return a list of human-readable data-quality issues (empty = clean)."""
    issues = []
    if df.empty:
        return [f"{name}: no rows"]
    times = pd.DatetimeIndex(df["start_utc"].unique()).sort_values()
    expected = pd.date_range(times.min(), times.max(), freq="30min")
    missing = expected.difference(times)
    if len(missing):
        issues.append(f"{name}: {len(missing)} missing half-hours "
                      f"(first {missing[0]:%Y-%m-%d %H:%M} UTC)")
    dups = df.duplicated(list(key)).sum()
    if dups:
        issues.append(f"{name}: {dups} duplicate rows")
    neg = df.loc[df["mw"] < 0]
    if name.startswith("BMRS"):
        # Expected negatives: interconnectors (exports) and pumped storage (pumping load).
        expected = neg["fuel"].str.startswith("INT") | (neg["fuel"] == "PS")
        if expected.any():
            issues.append(f"{name}: {int(expected.sum())} negative values from interconnector "
                          "exports or pumped-storage pumping (expected, not errors)")
        neg = neg.loc[~expected]
    if len(neg):
        issues.append(f"{name}: {len(neg)} negative generation values")
    return issues


def combine(bmrs: pd.DataFrame, solar: pd.DataFrame) -> pd.DataFrame:
    """Wide half-hourly table: one column per generation group plus Solar (embedded est.)."""
    domestic = bmrs[~bmrs["group"].isin(["Interconnector imports", "Pumped storage"])]
    wide = domestic.pivot_table(index="start_utc", columns="group", values="mw", aggfunc="sum")
    wide["Solar (PV_Live estimate)"] = solar.set_index("start_utc")["mw"]
    return wide.sort_index()


def monthly_energy_gwh(wide: pd.DataFrame) -> pd.DataFrame:
    """MW per half hour -> GWh per calendar month (UTC)."""
    gwh = wide * 0.5 / 1000
    return gwh.groupby(gwh.index.tz_convert(None).to_period("M")).sum().round(1)


def solar_share(wide: pd.DataFrame) -> dict:
    """Solar share of domestic generation with and without the embedded estimate."""
    solar_col = "Solar (PV_Live estimate)"
    bmrs_only = wide.drop(columns=[solar_col]).sum().sum()
    with_solar = wide.sum().sum()
    return {"bmrs_only_pct": 0.0,
            "with_embedded_pct": round(100 * wide[solar_col].sum() / with_solar, 2),
            "bmrs_total_gwh": round(bmrs_only * 0.5 / 1000, 1),
            "solar_gwh": round(wide[solar_col].sum() * 0.5 / 1000, 1)}
