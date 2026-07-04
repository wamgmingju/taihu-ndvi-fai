from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402


NODATA = -9999.0


def stats_pair(modis_values: np.ndarray, hls_values: np.ndarray) -> dict[str, float]:
    diff = modis_values - hls_values
    if len(diff) < 2:
        corr = math.nan
    else:
        corr = float(np.corrcoef(modis_values, hls_values)[0, 1])
    return {
        "modis_mean": float(np.mean(modis_values)),
        "hls_mean": float(np.mean(hls_values)),
        "bias_modis_minus_hls": float(np.mean(diff)),
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "corr": corr,
    }


def hls_mean_for_modis_pixel(hls_src, row: int, col: int, modis_transform):
    left, top = modis_transform * (col, row)
    right, bottom = modis_transform * (col + 1, row + 1)
    west, east = sorted([left, right])
    south, north = sorted([bottom, top])
    window = from_bounds(west, south, east, north, hls_src.transform)
    window = window.round_offsets().round_lengths()
    if window.width <= 0 or window.height <= 0:
        return None
    data = hls_src.read([1, 2, 4], window=window, boundless=True, fill_value=NODATA).astype("float64")
    ndvi, fai, qa = data[0], data[1], data[2]
    valid = (
        np.isfinite(ndvi)
        & np.isfinite(fai)
        & (ndvi != NODATA)
        & (fai != NODATA)
        & (qa > 0)
    )
    if not valid.any():
        return None
    return float(np.mean(ndvi[valid])), float(np.mean(fai[valid])), int(valid.sum())


def compare_date(date: str) -> dict[str, object] | None:
    hls_path = ROOT / "outputs" / "rasters" / "hls_observed_no_east_taihu" / f"Taihu_HLS_observed_NDVI_FAI_QA_{date}.tif"
    modis_path = (
        ROOT
        / "outputs"
        / "rasters"
        / "modis_daily_v2_fai1240_no_east_taihu"
        / f"Taihu_MODIS_daily_v2_NDVI_FAI1640_FAI1240_QA_{date}.tif"
    )
    if not hls_path.exists() or not modis_path.exists():
        return None

    with rasterio.open(hls_path) as hls, rasterio.open(modis_path) as modis:
        if hls.crs != modis.crs:
            raise ValueError(f"CRS mismatch for {date}: HLS={hls.crs}, MODIS={modis.crs}")
        modis_data = modis.read([1, 3, 4]).astype("float64")
        modis_ndvi, modis_fai1240, modis_qa = modis_data[0], modis_data[1], modis_data[2]
        modis_valid = (
            np.isfinite(modis_ndvi)
            & np.isfinite(modis_fai1240)
            & (modis_ndvi != (modis.nodata or NODATA))
            & (modis_fai1240 != (modis.nodata or NODATA))
            & (modis_qa > 0)
        )

        modis_ndvi_values = []
        modis_fai_values = []
        hls_ndvi_values = []
        hls_fai_values = []
        hls_source_pixels = []
        valid_rows, valid_cols = np.where(modis_valid)
        for row, col in zip(valid_rows, valid_cols):
            hls_mean = hls_mean_for_modis_pixel(hls, int(row), int(col), modis.transform)
            if hls_mean is None:
                continue
            hls_ndvi, hls_fai, hls_n = hls_mean
            modis_ndvi_values.append(float(modis_ndvi[row, col]))
            modis_fai_values.append(float(modis_fai1240[row, col]))
            hls_ndvi_values.append(hls_ndvi)
            hls_fai_values.append(hls_fai)
            hls_source_pixels.append(hls_n)

        row: dict[str, object] = {
            "date": date,
            "modis_valid_pixels": int(modis_valid.sum()),
            "paired_modis_pixels": len(modis_ndvi_values),
            "mean_hls_30m_pixels_per_modis_pair": float(np.mean(hls_source_pixels)) if hls_source_pixels else 0.0,
            "note": "FAI comparison is approximate because HLS FAI and MODIS FAI_1240 use different bandpasses.",
        }
        if not modis_ndvi_values:
            row["problem"] = "no_paired_valid_pixels"
            return row

        ndvi_stats = stats_pair(np.array(modis_ndvi_values), np.array(hls_ndvi_values))
        fai_stats = stats_pair(np.array(modis_fai_values), np.array(hls_fai_values))
        for key, value in ndvi_stats.items():
            row[f"ndvi_{key}"] = value
        for key, value in fai_stats.items():
            row[f"fai1240_vs_hls_{key}"] = value
        return row


def main() -> None:
    hls_dir = ROOT / "outputs" / "rasters" / "hls_observed_no_east_taihu"
    dates = sorted(path.stem.split("_")[-1] for path in hls_dir.glob("Taihu_HLS_observed_NDVI_FAI_QA_*.tif"))
    rows = [row for date in dates if (row := compare_date(date)) is not None]
    out = ensure_dir(ROOT / "outputs" / "tables") / "hls_modis_consistency_no_east_taihu.csv"
    fieldnames = sorted(set().union(*(row.keys() for row in rows))) if rows else ["date"]
    preferred = [
        "date",
        "modis_valid_pixels",
        "paired_modis_pixels",
        "mean_hls_30m_pixels_per_modis_pair",
        "ndvi_modis_mean",
        "ndvi_hls_mean",
        "ndvi_bias_modis_minus_hls",
        "ndvi_mae",
        "ndvi_rmse",
        "ndvi_corr",
        "fai1240_vs_hls_modis_mean",
        "fai1240_vs_hls_hls_mean",
        "fai1240_vs_hls_bias_modis_minus_hls",
        "fai1240_vs_hls_mae",
        "fai1240_vs_hls_rmse",
        "fai1240_vs_hls_corr",
        "problem",
        "note",
    ]
    fieldnames = [name for name in preferred if name in fieldnames] + [
        name for name in fieldnames if name not in preferred
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
