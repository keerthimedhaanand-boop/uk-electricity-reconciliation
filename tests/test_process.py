import pandas as pd

from src.process import (combine, monthly_energy_gwh, solar_share, tidy_bmrs,
                         tidy_pvlive, validate)


def bmrs_raw(times, fuels=("CCGT", "WIND", "INTFR"), mw=1000):
    return pd.DataFrame([{"startTime": t, "fuelType": f, "generation": mw}
                         for t in times for f in fuels])


def test_pvlive_shifted_from_period_end_to_start():
    raw = pd.DataFrame({"gsp_id": [0], "datetime_gmt": ["2026-10-01T12:30:00Z"],
                        "generation_mw": [5000.0]})
    out = tidy_pvlive(raw)
    assert out["start_utc"].iloc[0] == pd.Timestamp("2026-10-01T12:00:00Z")


def test_validate_finds_missing_half_hour_and_duplicates():
    times = ["2026-10-01T00:00:00Z", "2026-10-01T01:00:00Z"]  # 00:30 missing
    df = tidy_bmrs(bmrs_raw(times))
    issues = validate(df, "BMRS", key=("start_utc", "fuel"))
    assert any("1 missing" in i for i in issues)


def test_interconnectors_excluded_and_solar_added():
    t = ["2026-10-01T12:00:00Z"]
    bmrs = tidy_bmrs(bmrs_raw(t))
    solar = tidy_pvlive(pd.DataFrame({"gsp_id": [0], "datetime_gmt": ["2026-10-01T12:30:00Z"],
                                      "generation_mw": [2000.0]}))
    wide = combine(bmrs, solar)
    assert "Interconnector imports" not in wide.columns
    assert wide["Solar (PV_Live estimate)"].iloc[0] == 2000.0
    share = solar_share(wide)  # 2000 of (1000 gas + 1000 wind + 2000 solar)
    assert share["with_embedded_pct"] == 50.0


def test_monthly_energy_converts_mw_halfhours_to_gwh():
    idx = pd.date_range("2026-10-01", periods=48, freq="30min", tz="UTC")
    wide = pd.DataFrame({"Gas": 1000.0}, index=idx)  # 1 GW for 24 h = 24 GWh
    assert monthly_energy_gwh(wide)["Gas"].iloc[0] == 24.0
