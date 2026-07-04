from __future__ import annotations

import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import rasterio  # noqa: E402


INPUT_DIR = ROOT / "outputs" / "rasters" / "modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear"
OUTPUT_ROOT = ROOT / "outputs" / "rasters" / "final_daily_ndvi_fai_no_east_taihu"


def write_single_band(src, band_index: int, out_path: Path, description: str) -> None:
    profile = src.profile.copy()
    profile.update(count=1, dtype="float32", nodata=-9999.0, compress="deflate")
    data = src.read(band_index).astype("float32")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data, 1)
        dst.set_band_description(1, description)


def main() -> None:
    ndvi_dir = ensure_dir(OUTPUT_ROOT / "NDVI")
    fai_dir = ensure_dir(OUTPUT_ROOT / "FAI")
    status_dir = ensure_dir(OUTPUT_ROOT / "STATUS")
    files = sorted(INPUT_DIR.glob("Taihu_MODIS_gapfilled_linear_NDVI_FAI_STATUS_*.tif"))
    for path in files:
        date = path.stem.split("_")[-1]
        with rasterio.open(path) as src:
            write_single_band(src, 1, ndvi_dir / f"Taihu_NDVI_no_east_taihu_{date}.tif", "NDVI")
            write_single_band(src, 2, fai_dir / f"Taihu_FAI_no_east_taihu_{date}.tif", "FAI_MODIS_FAI1240")
            write_single_band(src, 3, status_dir / f"Taihu_STATUS_no_east_taihu_{date}.tif", "STATUS_30_observed_55_interpolated_90_missing")
    print(f"input_files={len(files)}")
    print(f"ndvi_files={len(list(ndvi_dir.glob('*.tif')))}")
    print(f"fai_files={len(list(fai_dir.glob('*.tif')))}")
    print(f"status_files={len(list(status_dir.glob('*.tif')))}")
    print(f"output_root={OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
