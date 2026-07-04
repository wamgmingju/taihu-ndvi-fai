from __future__ import annotations

import csv
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402


NODATA = -9999.0
PRODUCT_DIR = ROOT / "outputs" / "rasters" / "modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear"
SUMMARY_CSV = ROOT / "outputs" / "tables" / "modis_v2_fai1240_no_east_taihu_gapfilled_status_summary.csv"


def load_status_summary() -> list[dict[str, str]]:
    with SUMMARY_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def select_dates(rows: list[dict[str, str]]) -> list[str]:
    by_date = {row["date"]: row for row in rows}
    selected = ["20240501", "20240514", "20240518", "20240618", "20240730", "20240731"]
    max_observed = max(rows, key=lambda r: int(r["observed_pixels"]))["date"]
    max_interpolated = max(rows, key=lambda r: int(r["interpolated_pixels"]))["date"]
    max_missing = max(rows, key=lambda r: int(r["missing_pixels"]))["date"]
    for date in [max_observed, max_interpolated, max_missing]:
        if date not in selected and date in by_date:
            selected.append(date)
    return [date for date in selected if date in by_date]


def finite_stats(arr: np.ndarray, valid: np.ndarray) -> tuple[float, float, float]:
    values = arr[valid]
    if values.size == 0:
        return np.nan, np.nan, np.nan
    return float(values.min()), float(values.max()), float(values.mean())


def check_file(path: Path) -> dict[str, object]:
    date = path.stem.split("_")[-1]
    with rasterio.open(path) as src:
        data = src.read(masked=False).astype("float64")
        ndvi, fai, status, gap_days = data[0], data[1], data[2], data[3]
        valid_ndvi = np.isfinite(ndvi) & (ndvi != (src.nodata or NODATA))
        valid_fai = np.isfinite(fai) & (fai != (src.nodata or NODATA))
        valid_value = valid_ndvi & valid_fai & (status != 90)
        ndvi_min, ndvi_max, ndvi_mean = finite_stats(ndvi, valid_value)
        fai_min, fai_max, fai_mean = finite_stats(fai, valid_value)
        statuses, counts = np.unique(status[np.isfinite(status)], return_counts=True)
        status_counts = {int(k): int(v) for k, v in zip(statuses, counts)}
        problems: list[str] = []
        if str(src.crs) != "EPSG:32651":
            problems.append(f"crs={src.crs}")
        if src.count != 4:
            problems.append(f"band_count={src.count}")
        if abs(src.res[0] - 500) > 1e-6 or abs(abs(src.res[1]) - 500) > 1e-6:
            problems.append(f"res={src.res}")
        if src.nodata != NODATA:
            problems.append(f"nodata={src.nodata}")
        if valid_value.any() and (ndvi_min < -1.0001 or ndvi_max > 1.0001):
            problems.append(f"ndvi_range={ndvi_min:.4f}..{ndvi_max:.4f}")
        if valid_value.any() and (fai_min < -1 or fai_max > 1):
            problems.append(f"fai_range={fai_min:.4f}..{fai_max:.4f}")
        if not valid_value.any():
            problems.append("no_displayable_ndvi_fai_pixels")
        return {
            "date": date,
            "path": str(path.relative_to(ROOT)),
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "bands": src.count,
            "res_x": src.res[0],
            "res_y": src.res[1],
            "nodata": src.nodata,
            "ndvi_min": ndvi_min,
            "ndvi_max": ndvi_max,
            "ndvi_mean": ndvi_mean,
            "fai_min": fai_min,
            "fai_max": fai_max,
            "fai_mean": fai_mean,
            "status_30_observed": status_counts.get(30, 0),
            "status_55_interpolated": status_counts.get(55, 0),
            "status_90_missing": status_counts.get(90, 0),
            "problems": ";".join(problems),
        }


def render_quicklook(path: Path, out_dir: Path) -> Path:
    date = path.stem.split("_")[-1]
    with rasterio.open(path) as src:
        ndvi, fai, status = src.read([1, 2, 3]).astype("float64")
        nodata = src.nodata or NODATA
    ndvi = np.where((ndvi == nodata) | (status == 90), np.nan, ndvi)
    fai = np.where((fai == nodata) | (status == 90), np.nan, fai)
    status_masked = np.where(np.isfinite(status), status, np.nan)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4), constrained_layout=True)
    ndvi_img = axes[0].imshow(ndvi, cmap="RdYlGn", vmin=-0.6, vmax=0.4)
    axes[0].set_title(f"{date} NDVI")
    plt.colorbar(ndvi_img, ax=axes[0], fraction=0.046, pad=0.04)
    fai_img = axes[1].imshow(fai, cmap="viridis", vmin=-0.08, vmax=0.04)
    axes[1].set_title(f"{date} FAI")
    plt.colorbar(fai_img, ax=axes[1], fraction=0.046, pad=0.04)
    status_img = axes[2].imshow(status_masked, cmap="Set1", vmin=30, vmax=90)
    axes[2].set_title("STATUS")
    plt.colorbar(status_img, ax=axes[2], fraction=0.046, pad=0.04)
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    out = out_dir / f"quicklook_ndvi_fai_status_{date}.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def main() -> None:
    files = sorted(PRODUCT_DIR.glob("Taihu_MODIS_gapfilled_linear_NDVI_FAI_STATUS_*.tif"))
    rows = [check_file(path) for path in files]
    out_csv = ensure_dir(ROOT / "outputs" / "tables") / "gis_readiness_gapfilled_no_east_taihu.csv"
    fieldnames = list(rows[0].keys()) if rows else ["date"]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = load_status_summary()
    quicklook_dir = ensure_dir(ROOT / "outputs" / "quicklooks" / "gapfilled_no_east_taihu")
    selected_dates = select_dates(summary_rows)
    quicklooks = []
    for date in selected_dates:
        path = PRODUCT_DIR / f"Taihu_MODIS_gapfilled_linear_NDVI_FAI_STATUS_{date}.tif"
        if path.exists():
            quicklooks.append(render_quicklook(path, quicklook_dir))

    problem_count = sum(1 for row in rows if row["problems"])
    print(f"files={len(files)}")
    print(f"problem_files={problem_count}")
    print(f"wrote={out_csv}")
    for path in quicklooks:
        print(f"quicklook={path}")


if __name__ == "__main__":
    main()
