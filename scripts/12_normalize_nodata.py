from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


def normalize_file(path: Path, nodata: float = -9999.0) -> bool:
    with rasterio.open(path) as src:
        data = src.read(masked=False)
        profile = src.profile.copy()
        needs_update = src.nodata != nodata or np.isneginf(data).any() or np.isposinf(data).any()
        if not needs_update:
            return False
        data = data.astype("float32", copy=False)
        data[~np.isfinite(data)] = nodata
        profile.update(dtype="float32", nodata=nodata, compress="DEFLATE", predictor=2)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(data)
    tmp.replace(path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace infinite GeoTIFF nodata values with explicit -9999.")
    parser.add_argument("--glob", default="outputs/rasters/modis_daily/*.tif")
    parser.add_argument("--nodata", type=float, default=-9999.0)
    args = parser.parse_args()

    files = sorted(ROOT.glob(args.glob))
    changed = 0
    for path in files:
        if normalize_file(path, args.nodata):
            changed += 1
            print(f"normalized {path}")
    print(f"checked={len(files)} changed={changed}")


if __name__ == "__main__":
    main()
