from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


STATUS_OBSERVED = 30
STATUS_INTERPOLATED = 55
STATUS_MISSING = 90
NODATA = -9999.0


def parse_date(path: Path) -> dt.date:
    return dt.datetime.strptime(path.stem.split("_")[-1], "%Y%m%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a simple linear time-interpolated MODIS NDVI/FAI layer.")
    parser.add_argument("--max-gap-days", type=int, default=10, help="Do not fill if nearest observation is farther than this.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--input-dir", default="modis_daily")
    parser.add_argument("--output-dir", default="modis_daily_gapfilled_linear")
    args = parser.parse_args()

    in_dir = ROOT / "outputs" / "rasters" / args.input_dir
    out_dir = ensure_dir(ROOT / "outputs" / "rasters" / args.output_dir)
    files = sorted(in_dir.glob("*.tif"))
    if not files:
        raise RuntimeError(f"No MODIS files found in {in_dir}")

    dates = [parse_date(path) for path in files]
    day_numbers = np.array([(d - dates[0]).days for d in dates], dtype="float32")
    with rasterio.open(files[0]) as src0:
        profile = src0.profile.copy()
        height, width = src0.height, src0.width
        transform = src0.transform

    ndvi = np.full((len(files), height, width), np.nan, dtype="float32")
    fai = np.full_like(ndvi, np.nan)
    observed = np.zeros((len(files), height, width), dtype=bool)
    for i, path in enumerate(files):
        with rasterio.open(path) as src:
            arr = src.read(masked=False).astype("float32")
            file_nodata = src.nodata if src.nodata is not None else NODATA
            qa_band_index = 3 if src.count >= 6 else 2
            fai_band_index = 2 if src.count >= 6 else 1
            valid = (
                np.isfinite(arr[0])
                & np.isfinite(arr[1])
                & (arr[0] != file_nodata)
                & (arr[fai_band_index] != file_nodata)
                & (arr[qa_band_index] > 0)
            )
            ndvi[i][valid] = arr[0][valid]
            fai[i][valid] = arr[fai_band_index][valid]
            observed[i] = valid

    flat_ndvi = ndvi.reshape(len(files), -1)
    flat_fai = fai.reshape(len(files), -1)
    flat_obs = observed.reshape(len(files), -1)
    filled_ndvi = np.full_like(flat_ndvi, NODATA)
    filled_fai = np.full_like(flat_fai, NODATA)
    status = np.full(flat_ndvi.shape, STATUS_MISSING, dtype="float32")
    gap_days = np.full(flat_ndvi.shape, NODATA, dtype="float32")

    for px in range(flat_ndvi.shape[1]):
        valid_idx = np.where(flat_obs[:, px])[0]
        if valid_idx.size == 0:
            continue
        filled_ndvi[valid_idx, px] = flat_ndvi[valid_idx, px]
        filled_fai[valid_idx, px] = flat_fai[valid_idx, px]
        status[valid_idx, px] = STATUS_OBSERVED
        gap_days[valid_idx, px] = 0
        if valid_idx.size < 2:
            continue
        first, last = valid_idx[0], valid_idx[-1]
        target_idx = np.arange(first, last + 1)
        interp_ndvi = np.interp(day_numbers[target_idx], day_numbers[valid_idx], flat_ndvi[valid_idx, px])
        interp_fai = np.interp(day_numbers[target_idx], day_numbers[valid_idx], flat_fai[valid_idx, px])
        for local_pos, idx in enumerate(target_idx):
            nearest = np.min(np.abs(day_numbers[valid_idx] - day_numbers[idx]))
            if nearest <= args.max_gap_days and not flat_obs[idx, px]:
                filled_ndvi[idx, px] = interp_ndvi[local_pos]
                filled_fai[idx, px] = interp_fai[local_pos]
                status[idx, px] = STATUS_INTERPOLATED
                gap_days[idx, px] = nearest

    filled_ndvi = filled_ndvi.reshape(len(files), height, width)
    filled_fai = filled_fai.reshape(len(files), height, width)
    status = status.reshape(len(files), height, width)
    gap_days = gap_days.reshape(len(files), height, width)

    profile.update(count=4, dtype="float32", nodata=NODATA, compress="DEFLATE", predictor=2)
    for i, day in enumerate(dates):
        ymd = day.strftime("%Y%m%d")
        out = out_dir / f"Taihu_MODIS_gapfilled_linear_NDVI_FAI_STATUS_{ymd}.tif"
        if out.exists() and not args.overwrite:
            continue
        data = np.stack([filled_ndvi[i], filled_fai[i], status[i], gap_days[i]]).astype("float32")
        with rasterio.open(out, "w", **profile) as dst:
            dst.write(data)
            dst.set_band_description(1, "NDVI")
            dst.set_band_description(2, "FAI")
            dst.set_band_description(3, "STATUS_30_observed_55_interpolated_90_missing")
            dst.set_band_description(4, "NEAREST_OBS_GAP_DAYS")

    observed_pixels = int((status == STATUS_OBSERVED).sum())
    interpolated_pixels = int((status == STATUS_INTERPOLATED).sum())
    missing_pixels = int((status == STATUS_MISSING).sum())
    print(f"files={len(files)}")
    print(f"observed_pixels={observed_pixels}")
    print(f"interpolated_pixels={interpolated_pixels}")
    print(f"missing_pixels={missing_pixels}")
    print(f"out_dir={out_dir}")


if __name__ == "__main__":
    main()
