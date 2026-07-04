from __future__ import annotations

import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


SRC_DIR = ROOT / "outputs" / "rasters" / "final_daily_ndvi_fai_no_east_taihu" / "STATUS"
OUT_DIR = ROOT / "outputs" / "rasters" / "final_daily_ndvi_fai_no_east_taihu" / "STATUS_uint8_arcgis"
NODATA = 255


def main() -> None:
    ensure_dir(OUT_DIR)
    files = sorted(SRC_DIR.glob("Taihu_STATUS_no_east_taihu_*.tif"))
    for path in files:
        date = path.stem.split("_")[-1]
        with rasterio.open(path) as src:
            arr = src.read(1)
            out = np.full(arr.shape, NODATA, dtype="uint8")
            out[arr == 30] = 30
            out[arr == 55] = 55
            out[arr == 90] = 90
            profile = src.profile.copy()
            profile.update(dtype="uint8", count=1, nodata=NODATA, compress="deflate")
            out_path = OUT_DIR / f"Taihu_STATUS_uint8_no_east_taihu_{date}.tif"
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(out, 1)
                dst.set_band_description(1, "STATUS_uint8_30_observed_55_interpolated_90_missing_255_nodata")
                dst.write_colormap(
                    1,
                    {
                        30: (0, 176, 80, 255),
                        55: (255, 192, 0, 255),
                        90: (160, 160, 160, 255),
                        255: (0, 0, 0, 0),
                    },
                )
    print(f"input_files={len(files)}")
    print(f"output_files={len(list(OUT_DIR.glob('*.tif')))}")
    print(f"out_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
