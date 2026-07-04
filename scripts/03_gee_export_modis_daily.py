from __future__ import annotations

import argparse

from common import add_common_args, configured_dates, project_config, sensor_registry


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description="Export Terra, Aqua, and Terra+Aqua MODIS daily coarse evidence separately."))
    args = parser.parse_args()
    cfg = project_config()
    sensors = sensor_registry()
    dates = configured_dates(args)
    selected = ["MODIS_TERRA", "MODIS_AQUA"]

    if args.dry_run:
        for day in dates:
            for key in selected:
                print(f"{day} {key}: would export coarse FAI/NDVI/QA from {sensors[key]['collection']}")
            print(f"{day} MODIS_TA_BEST: would export best-pixel composite without overwriting Terra/Aqua lineage")
        return

    import ee

    ee.Initialize(project=cfg["gee_project"])
    roi = ee.Geometry.Rectangle(cfg["aoi"]["bbox_wgs84"])

    def mask_modis(image):
        state = image.select("state_1km")
        qc = image.select("QC_500m").bitwiseAnd(3)
        cloud_state = state.bitwiseAnd(3)
        cloud_shadow = state.rightShift(2).bitwiseAnd(1)
        aerosol = state.rightShift(6).bitwiseAnd(3)
        cirrus = state.rightShift(8).bitwiseAnd(3)
        internal_cloud = state.rightShift(10).bitwiseAnd(1)
        adjacent_cloud = state.rightShift(13).bitwiseAnd(1)
        clear = (cloud_state.eq(0)
                 .And(cloud_shadow.eq(0))
                 .And(aerosol.lt(3))
                 .And(cirrus.lte(1))
                 .And(internal_cloud.eq(0))
                 .And(adjacent_cloud.eq(0))
                 .And(qc.lte(1)))
        quality = (ee.Image.constant(100)
                   .subtract(aerosol.multiply(20))
                   .subtract(cirrus.multiply(10))
                   .subtract(qc.multiply(5))
                   .rename("QUALITY"))
        return image.updateMask(clear).addBands(quality)

    def add_indices(image, meta, qa_value, source_value):
        bands = meta["bands"]
        wl = meta["wavelength_nm"]
        scale = meta["scale_factor"]
        red = image.select(bands["red"]).multiply(scale)
        nir = image.select(bands["nir"]).multiply(scale)
        swir = image.select(bands["swir1"]).multiply(scale)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        baseline = red.add(swir.subtract(red).multiply((wl["nir"] - wl["red"]) / (wl["swir1"] - wl["red"])))
        fai = nir.subtract(baseline).rename("FAI")
        qa = ee.Image.constant(qa_value).rename("QA").toByte().updateMask(ndvi.mask())
        source = ee.Image.constant(source_value).rename("SOURCE").toByte().updateMask(ndvi.mask())
        quality = image.select("QUALITY").updateMask(ndvi.mask())
        return ndvi.addBands([fai, qa, source, quality])

    for day in dates:
        start = ee.Date(day.isoformat())
        end = start.advance(1, "day")
        daily_images = []
        for key in selected:
            meta = sensors[key]
            col = ee.ImageCollection(meta["collection"]).filterBounds(roi).filterDate(start, end).map(mask_modis)
            source_value = 1 if key == "MODIS_TERRA" else 2
            img = add_indices(col.median().clip(roi), meta, 30, source_value)
            daily_images.append(img)
            desc = f"codex_{key}_{day.strftime('%Y%m%d')}"
            task = ee.batch.Export.image.toDrive(
                image=img,
                description=desc,
                folder="taihu_codex_modis",
                fileNamePrefix=desc,
                region=roi,
                scale=meta["native_resolution_m"],
                crs=cfg["grid"]["analysis_crs"],
                maxPixels=1e13
            )
            task.start()
            print(f"Started {desc}")
        composite = ee.ImageCollection(daily_images).qualityMosaic("QUALITY")
        desc = f"codex_MODIS_TA_BEST_{day.strftime('%Y%m%d')}"
        ee.batch.Export.image.toDrive(
            image=composite,
            description=desc,
            folder="taihu_codex_modis",
            fileNamePrefix=desc,
            region=roi,
            scale=cfg["grid"]["modis_native_m"],
            crs=cfg["grid"]["analysis_crs"],
            maxPixels=1e13
        ).start()
        print(f"Started {desc}")


if __name__ == "__main__":
    main()
