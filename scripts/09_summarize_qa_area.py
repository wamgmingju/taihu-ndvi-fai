from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import ROOT, ensure_dir, project_config, qa_codes

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize area by QA code using projected raster pixel size.")
    parser.add_argument("--qa-dir", default=str(ROOT / "outputs" / "rasters"))
    args = parser.parse_args()
    cfg = project_config()
    qa_meta = qa_codes()
    paths = sorted(Path(args.qa_dir).rglob("*QA*.tif"))
    if not paths:
        print(f"No QA rasters found under {args.qa_dir}.")
        return

    import rasterio

    rows = []
    for path in paths:
        with rasterio.open(path) as src:
            qa = src.read(1)
            crs = str(src.crs)
            if crs != cfg["grid"]["analysis_crs"]:
                raise ValueError(
                    f"{path} CRS is {crs}; expected {cfg['grid']['analysis_crs']} before direct area calculation."
                )
            pixel_area_km2 = abs(src.transform.a * src.transform.e) / 1_000_000
            for code, meta in qa_meta.items():
                count = int((qa == int(code)).sum())
                rows.append({
                    "file": str(path),
                    "qa": code,
                    "qa_name": meta["name"],
                    "pixel_count": count,
                    "area_km2": count * pixel_area_km2,
                    "use_for_final_area": meta["use_for_final_area"]
                })
    out = ensure_dir(ROOT / "outputs" / "tables") / "daily_area_by_qa.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
