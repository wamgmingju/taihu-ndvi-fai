from __future__ import annotations

import csv
import sys
from pathlib import Path

import argparse

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize gap-filled STATUS bands.")
    parser.add_argument("--input-dir", default="modis_daily_gapfilled_linear")
    parser.add_argument("--output", default="modis_gapfilled_status_summary.csv")
    args = parser.parse_args()
    in_dir = ROOT / "outputs" / "rasters" / args.input_dir
    files = sorted(in_dir.glob("Taihu_MODIS_gapfilled_linear_NDVI_FAI_STATUS_*.tif"))
    out = ensure_dir(ROOT / "outputs" / "tables") / args.output
    rows = []
    for path in files:
        date = path.stem.split("_")[-1]
        with rasterio.open(path) as src:
            status = src.read(3)
            total = status.size
            observed = int((status == 30).sum())
            interpolated = int((status == 55).sum())
            missing = int((status == 90).sum())
            rows.append(
                {
                    "date": date,
                    "observed_pixels": observed,
                    "interpolated_pixels": interpolated,
                    "missing_pixels": missing,
                    "observed_fraction": observed / total,
                    "interpolated_fraction": interpolated / total,
                    "missing_fraction": missing / total,
                }
            )
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
