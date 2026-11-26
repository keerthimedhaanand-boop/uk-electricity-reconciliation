# Methods

## Sources

| Source | What it measures | Time stamp | Access |
|---|---|---|---|
| Elexon BMRS FUELHH | Transmission-connected generation by fuel type, MW averaged per half hour | `startTime`, UTC, start of period | `data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH` |
| Sheffield Solar PV_Live (GSP 0) | Modelled national solar generation, MW | `datetime_gmt`, UTC, **end** of period | `api.pvlive.uk/pvlive/api/v4/gsp/0` |

Retrieval dates are the dates the pipeline is run; re-running may return revised values.

## Definitions

- **Time:** every row is keyed by the UTC start of a 30-minute period. Using UTC avoids the 46- and
  50-period settlement days at clock changes.
- **Energy:** MWh = MW x 0.5. Monthly totals are reported in GWh.
- **Domestic generation:** all FUELHH fuels except interconnectors (`INT*`, imports) and pumped
  storage (`PS`, which mostly re-generates electricity bought earlier), plus the PV_Live solar estimate.

## Validation checks

- Every half-hour between the first and last timestamp is present.
- No duplicate rows per time (and per fuel for BMRS).
- No negative generation outside interconnectors.

Issues are reported in `outputs/report.md`, not silently fixed.

## Known limitations

- PV_Live solar is **modelled**, not metered, and is revised as more data arrives.
- Embedded wind is not yet added, so wind is still understated (see README roadmap).
- Combining BMRS with PV_Live gives an estimate of total generation; it will still not match DESNZ
  Energy Trends exactly, because of differences in coverage (e.g. autogeneration) and in methodology.
