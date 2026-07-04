from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from common import ROOT, add_common_args, configured_dates, ensure_dir, project_config, sensor_registry


def load_daily_module():
    path = ROOT / "scripts" / "10_gee_process_daily.py"
    spec = importlib.util.spec_from_file_location("gee_daily", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modis_daily_v2_image(ee, daily, date_text: str, roi, water):
    sensors = sensor_registry()
    start = ee.Date(date_text)
    end = start.advance(1, "day")

    def add_indices(img, meta, source_value):
        bands = meta["bands"]
        scale = meta["scale_factor"]
        red = img.select(bands["red"]).multiply(scale)
        nir = img.select(bands["nir"]).multiply(scale)
        swir1640 = img.select(bands["swir1"]).multiply(scale)
        swir1240 = img.select(bands["swir1240"]).multiply(scale)
        refl_valid = (
            red.gt(0).And(red.lt(1))
            .And(nir.gt(0)).And(nir.lt(1))
            .And(swir1640.gt(0)).And(swir1640.lt(1))
            .And(swir1240.gt(0)).And(swir1240.lt(1))
            .And(nir.add(red).abs().gt(1e-6))
        )
        red = red.updateMask(refl_valid)
        nir = nir.updateMask(refl_valid)
        swir1640 = swir1640.updateMask(refl_valid)
        swir1240 = swir1240.updateMask(refl_valid)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        wl = meta["wavelength_nm"]
        baseline1640 = red.add(swir1640.subtract(red).multiply((wl["nir"] - wl["red"]) / (wl["swir1"] - wl["red"])))
        baseline1240 = red.add(swir1240.subtract(red).multiply((wl["nir"] - wl["red"]) / (wl["swir1240"] - wl["red"])))
        fai1640 = nir.subtract(baseline1640).rename("FAI_1640")
        fai1240 = nir.subtract(baseline1240).rename("FAI_1240")
        qa = ee.Image.constant(30).rename("QA").toByte().updateMask(ndvi.mask())
        source = ee.Image.constant(source_value).rename("SOURCE").toByte().updateMask(ndvi.mask())
        quality = img.select("QUALITY").updateMask(ndvi.mask())
        return ndvi.addBands([fai1640, fai1240, qa, source, quality])

    daily_images = []
    for key, source_value in [("MODIS_TERRA", 1), ("MODIS_AQUA", 2)]:
        meta = sensors[key]
        col = (
            ee.ImageCollection(meta["collection"])
            .filterBounds(roi)
            .filterDate(start, end)
            .map(lambda image: daily.modis_mask(ee, image))
        )
        img = add_indices(col.median().clip(roi).updateMask(water), meta, source_value)
        daily_images.append(img)
    return (
        ee.ImageCollection(daily_images)
        .qualityMosaic("QUALITY")
        .select(["NDVI", "FAI_1640", "FAI_1240", "QA", "SOURCE", "QUALITY"])
        .toFloat()
    )


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description="Download MODIS daily v2 with FAI_1640 and FAI_1240."))
    parser.add_argument("--max-days", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output-dir", default="modis_daily_v2_fai1240")
    args = parser.parse_args()

    daily = load_daily_module()
    ee, cfg = daily.initialize_ee()
    roi = daily.region_geometry(ee, cfg)
    water = daily.stable_water_mask(ee)
    dates = configured_dates(args)
    if args.max_days and args.max_days > 0:
        dates = dates[: args.max_days]

    out_dir = ensure_dir(ROOT / "outputs" / "rasters" / args.output_dir)
    errors = []
    for day in dates:
        date_text = day.isoformat()
        ymd = day.strftime("%Y%m%d")
        out = out_dir / f"Taihu_MODIS_daily_v2_NDVI_FAI1640_FAI1240_QA_{ymd}.tif"
        if out.exists() and not args.overwrite:
            print(f"skip {date_text}: output exists")
            continue
        image = modis_daily_v2_image(ee, daily, date_text, roi, water)
        try:
            daily.download_image(ee, image, roi, out, cfg["grid"]["modis_native_m"], cfg["grid"]["analysis_crs"])
        except Exception as exc:
            print(f"ERROR {date_text}: {exc}")
            errors.append({"date": date_text, "product": "modis_v2_fai1240", "error": repr(exc)})
    if errors:
        err_path = ensure_dir(ROOT / "reports") / "modis_v2_download_errors.json"
        err_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote errors to {err_path}")


if __name__ == "__main__":
    main()
