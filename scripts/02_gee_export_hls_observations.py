from __future__ import annotations

import argparse

from common import add_common_args, configured_dates, project_config, sensor_registry


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description="Export HLS same-day high-resolution observation layers."))
    args = parser.parse_args()
    cfg = project_config()
    sensors = sensor_registry()
    dates = configured_dates(args)
    selected = ["HLS_L30", "HLS_S30"]

    if args.dry_run:
        for day in dates:
            for key in selected:
                print(f"{day} {key}: would export NDVI/FAI/MNDWI/QA from {sensors[key]['collection']}")
        return

    import ee

    ee.Initialize(project=cfg["gee_project"])
    roi = ee.Geometry.Rectangle(cfg["aoi"]["bbox_wgs84"])

    def mask_hls(image):
        # HLS Fmask uses bit flags. Keep the water bit if present; reject problem bits.
        fmask = image.select("Fmask")
        cirrus = fmask.bitwiseAnd(1).eq(0)
        cloud = fmask.rightShift(1).bitwiseAnd(1).eq(0)
        adjacent = fmask.rightShift(2).bitwiseAnd(1).eq(0)
        shadow = fmask.rightShift(3).bitwiseAnd(1).eq(0)
        snow_ice = fmask.rightShift(4).bitwiseAnd(1).eq(0)
        aerosol_not_high = fmask.rightShift(6).bitwiseAnd(3).lt(3)
        clear = cirrus.And(cloud).And(adjacent).And(shadow).And(snow_ice).And(aerosol_not_high)
        return image.updateMask(clear)

    for day in dates:
        start = ee.Date(day.isoformat())
        end = start.advance(1, "day")
        for key in selected:
            meta = sensors[key]
            bands = meta["bands"]
            wl = meta["wavelength_nm"]
            col = (ee.ImageCollection(meta["collection"])
                   .filterBounds(roi)
                   .filterDate(start, end)
                   .map(mask_hls))
            img = col.median().clip(roi)
            scale = meta["scale_factor"]
            red = img.select(bands["red"]).multiply(scale)
            nir = img.select(bands["nir"]).multiply(scale)
            swir = img.select(bands["swir1"]).multiply(scale)
            green = img.select(bands["green"]).multiply(scale)
            ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
            baseline = red.add(swir.subtract(red).multiply((wl["nir"] - wl["red"]) / (wl["swir1"] - wl["red"])))
            fai = nir.subtract(baseline).rename("FAI")
            mndwi = green.subtract(swir).divide(green.add(swir)).rename("MNDWI")
            qa = ee.Image.constant(10).rename("QA").toByte().updateMask(ndvi.mask())
            out = ndvi.addBands([fai, mndwi, qa])
            desc = f"codex_HLS_{key}_{day.strftime('%Y%m%d')}"
            task = ee.batch.Export.image.toDrive(
                image=out,
                description=desc,
                folder="taihu_codex_hls",
                fileNamePrefix=desc,
                region=roi,
                scale=cfg["grid"]["high_resolution_m"],
                crs=cfg["grid"]["analysis_crs"],
                maxPixels=1e13
            )
            task.start()
            print(f"Started {desc}")


if __name__ == "__main__":
    main()
