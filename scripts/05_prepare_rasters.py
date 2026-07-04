from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, project_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Check and prepare exported rasters for analysis CRS and AOI clipping.")
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "rasters"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cfg = project_config()
    input_dir = Path(args.input_dir)
    rasters = sorted(input_dir.rglob("*.tif"))
    if not rasters:
        print(f"No rasters found in {input_dir}. Export data first.")
        return

    import rasterio

    for path in rasters:
        with rasterio.open(path) as src:
            print({
                "file": str(path),
                "crs": str(src.crs),
                "resolution": src.res,
                "shape": (src.height, src.width),
                "nodata": src.nodata,
                "target_analysis_crs": cfg["grid"]["analysis_crs"]
            })
        if args.dry_run:
            continue
        # Reprojection and AOI clipping should be implemented after real AOI vectors are supplied.
        # Keeping this explicit prevents silently doing bbox-only statistics.
        raise RuntimeError("Provide AOI vectors before enabling reprojection/clipping.")


if __name__ == "__main__":
    main()

