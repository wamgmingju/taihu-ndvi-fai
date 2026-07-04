from __future__ import annotations

import argparse

from common import add_common_args, configured_dates, project_config, sensor_registry


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description="Prepare Sentinel-3 OLCI auxiliary evidence exports."))
    args = parser.parse_args()
    cfg = project_config()
    meta = sensor_registry()["S3_OLCI"]
    dates = configured_dates(args)

    warning = (
        "COPERNICUS/S3/OLCI in GEE is L1 EFR TOA radiance. "
        "This script treats it as auxiliary evidence only, not as quantitative L2 water color."
    )

    if args.dry_run:
        print(warning)
        for day in dates:
            print(f"{day} S3_OLCI: would count/export auxiliary radiance evidence from {meta['collection']}")
        return

    import ee

    ee.Initialize(project=cfg["gee_project"])
    roi = ee.Geometry.Rectangle(cfg["aoi"]["bbox_wgs84"])
    print(warning)
    for day in dates:
        start = ee.Date(day.isoformat())
        end = start.advance(1, "day")
        col = ee.ImageCollection(meta["collection"]).filterBounds(roi).filterDate(start, end)
        img = col.median().clip(roi)
        desc = f"codex_S3_OLCI_AUX_{day.strftime('%Y%m%d')}"
        ee.batch.Export.image.toDrive(
            image=img,
            description=desc,
            folder="taihu_codex_olci_aux",
            fileNamePrefix=desc,
            region=roi,
            scale=meta["native_resolution_m"],
            crs=cfg["grid"]["analysis_crs"],
            maxPixels=1e13
        ).start()
        print(f"Started {desc}")


if __name__ == "__main__":
    main()

