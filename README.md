# UK electricity reconciliation

An open, reproducible pipeline that shows and fixes a common pitfall in Great Britain power data.

## The problem

Elexon's BMRS "generation by fuel type" data (FUELHH) only covers generation metered on the
**transmission** system. Most solar and much onshore wind is **embedded** in distribution networks,
so it never appears in BMRS: it shows up as lower demand instead. FUELHH has no solar category at all.
Calculating a renewable share straight from BMRS therefore understates solar and overstates gas, and
BMRS totals will not match DESNZ Energy Trends, which counts all generation.

## What this pipeline does

1. Downloads half-hourly BMRS FUELHH data (Elexon Insights API, no key needed).
2. Downloads Sheffield Solar PV_Live national solar estimates (no key needed).
3. Aligns both to UTC half-hour **start** times (PV_Live labels periods by their end).
4. Validates each source: missing half-hours, duplicates, negative values.
5. Combines them, excluding interconnector imports and pumped storage from domestic generation.
6. Writes CSVs, a generation-mix chart, monthly energy totals and a validation report.

## Run it

```bash
pip install -r requirements.txt
python run.py --start 2026-10-01 --end 2026-10-31
pytest            # unit tests for alignment, validation and unit conversions
```

Outputs: `data/` (clean CSVs), `outputs/generation_mix.png`, `outputs/monthly_gwh.csv`,
`outputs/report.md`.

## Roadmap

- [ ] Add NESO embedded wind estimates (transmission wind in BMRS misses embedded wind too).
- [ ] Reconcile monthly totals against DESNZ Energy Trends and report the gap per fuel.
- [ ] Weekly automatic refresh with GitHub Actions (workflow included, see `.github/workflows`).
- [ ] Electricity price data and an electrification analysis.

See [METHODS.md](METHODS.md) for sources, definitions and known limitations.
