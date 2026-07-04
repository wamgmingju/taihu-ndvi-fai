from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import ROOT, ensure_dir, project_config

import numpy as np


def otsu_threshold(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    hist, edges = np.histogram(values, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2
    weight1 = np.cumsum(hist)
    weight2 = np.cumsum(hist[::-1])[::-1]
    mean1 = np.cumsum(hist * centers) / np.maximum(weight1, 1)
    mean2 = (np.cumsum((hist * centers)[::-1]) / np.maximum(weight2[::-1], 1))[::-1]
    variance12 = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
    return float(centers[:-1][np.argmax(variance12)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FAI threshold sensitivity on exported FAI rasters.")
    parser.add_argument("--fai-dir", default=str(ROOT / "outputs" / "rasters"))
    args = parser.parse_args()
    cfg = project_config()
    thresholds = cfg["thresholds"]["fai_candidate"]
    paths = sorted(Path(args.fai_dir).rglob("*FAI*.tif"))
    if not paths:
        print(f"No FAI rasters found under {args.fai_dir}.")
        return

    import rasterio

    rows = []
    for path in paths:
        with rasterio.open(path) as src:
            fai = src.read(1).astype("float64")
            if src.nodata is not None:
                fai[fai == src.nodata] = np.nan
            finite = np.isfinite(fai)
            otsu = otsu_threshold(fai[finite])
            row = {"file": str(path), "valid_pixels": int(finite.sum()), "otsu": otsu}
            for th in thresholds:
                row[f"area_pixels_fai_gt_{th}"] = int(np.logical_and(finite, fai > th).sum())
            rows.append(row)

    out = ensure_dir(ROOT / "outputs" / "tables") / "fai_threshold_sensitivity.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
