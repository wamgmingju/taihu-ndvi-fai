from __future__ import annotations

import argparse
import csv
import io
import json
import time
import zipfile
from pathlib import Path

from common import ROOT, add_common_args, configured_dates, ensure_dir, project_config, sensor_registry


def initialize_ee():
    import ee

    cfg = project_config()
    last_error = None
    for attempt in range(1, 6):
        try:
            ee.Initialize(project=cfg["gee_project"])
            return ee, cfg
        except Exception as exc:
            last_error = exc
            print(f"ee.Initialize failed attempt {attempt}: {exc}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"Could not initialize Earth Engine: {last_error}")


def region_geometry(ee, cfg):
    vector_path = ROOT / cfg["aoi"].get("preferred_vector", "")
    if vector_path.exists():
        geojson = json.loads(vector_path.read_text(encoding="utf-8"))
        feature = geojson["features"][0] if geojson.get("type") == "FeatureCollection" else geojson
        geometry = feature["geometry"] if feature.get("type") == "Feature" else feature
        return ee.Geometry(geometry)
    return ee.Geometry.Rectangle(cfg["aoi"]["bbox_wgs84"])


def stable_water_mask(ee):
    return ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gte(75)


def hls_mask(image):
    fmask = image.select("Fmask")
    cirrus = fmask.bitwiseAnd(1).eq(0)
    cloud = fmask.rightShift(1).bitwiseAnd(1).eq(0)
    adjacent = fmask.rightShift(2).bitwiseAnd(1).eq(0)
    shadow = fmask.rightShift(3).bitwiseAnd(1).eq(0)
    snow_ice = fmask.rightShift(4).bitwiseAnd(1).eq(0)
    aerosol_not_high = fmask.rightShift(6).bitwiseAnd(3).lt(3)
    clear = cirrus.And(cloud).And(adjacent).And(shadow).And(snow_ice).And(aerosol_not_high)
    return image.updateMask(clear)


def hls_common_image(ee, date_text: str, roi, water):
    sensors = sensor_registry()
    start = ee.Date(date_text)
    end = start.advance(1, "day")

    def prep_l30(img):
        meta = sensors["HLS_L30"]
        bands = meta["bands"]
        scale = meta["scale_factor"]
        return (hls_mask(img)
                .select([bands["red"], bands["nir"], bands["swir1"], bands["green"]], ["red", "nir", "swir1", "green"])
                .multiply(scale)
                .copyProperties(img, img.propertyNames()))

    def prep_s30(img):
        meta = sensors["HLS_S30"]
        bands = meta["bands"]
        scale = meta["scale_factor"]
        return (hls_mask(img)
                .select([bands["red"], bands["nir"], bands["swir1"], bands["green"]], ["red", "nir", "swir1", "green"])
                .multiply(scale)
                .copyProperties(img, img.propertyNames()))

    l30 = ee.ImageCollection(sensors["HLS_L30"]["collection"]).filterBounds(roi).filterDate(start, end).map(prep_l30)
    s30 = ee.ImageCollection(sensors["HLS_S30"]["collection"]).filterBounds(roi).filterDate(start, end).map(prep_s30)
    merged = l30.merge(s30)
    base = merged.median().clip(roi).updateMask(water)
    red = base.select("red")
    nir = base.select("nir")
    swir = base.select("swir1")
    green = base.select("green")
    refl_valid = (red.gt(0).And(red.lt(1))
                  .And(nir.gt(0)).And(nir.lt(1))
                  .And(swir.gt(0)).And(swir.lt(1))
                  .And(green.gt(0)).And(green.lt(1))
                  .And(nir.add(red).abs().gt(1e-6))
                  .And(green.add(swir).abs().gt(1e-6)))
    red = red.updateMask(refl_valid)
    nir = nir.updateMask(refl_valid)
    swir = swir.updateMask(refl_valid)
    green = green.updateMask(refl_valid)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    # HLS L30/S30 use slightly different bandpasses; 665/865/1610 is a practical common baseline.
    baseline = red.add(swir.subtract(red).multiply((865 - 665) / (1610 - 665)))
    fai = nir.subtract(baseline).rename("FAI")
    mndwi = green.subtract(swir).divide(green.add(swir)).rename("MNDWI")
    qa = ee.Image.constant(10).rename("QA").toByte().updateMask(ndvi.mask())
    source = ee.Image.constant(10).rename("SOURCE").toByte().updateMask(ndvi.mask())
    return ndvi.addBands([fai, mndwi, qa, source]).toFloat()


def collection_count(ee, collection_id: str, date_text: str, roi) -> int:
    start = ee.Date(date_text)
    end = start.advance(1, "day")
    value = get_info_with_retry(ee.ImageCollection(collection_id).filterBounds(roi).filterDate(start, end).size())
    return int(value)


def hls_count(ee, date_text: str, roi) -> int:
    sensors = sensor_registry()
    return (collection_count(ee, sensors["HLS_L30"]["collection"], date_text, roi)
            + collection_count(ee, sensors["HLS_S30"]["collection"], date_text, roi))


def modis_counts(ee, date_text: str, roi) -> tuple[int, int]:
    sensors = sensor_registry()
    terra = collection_count(ee, sensors["MODIS_TERRA"]["collection"], date_text, roi)
    aqua = collection_count(ee, sensors["MODIS_AQUA"]["collection"], date_text, roi)
    return terra, aqua


def modis_mask(ee, image):
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


def modis_daily_image(ee, date_text: str, roi, water):
    sensors = sensor_registry()
    start = ee.Date(date_text)
    end = start.advance(1, "day")

    def add_indices(img, meta, source_value):
        bands = meta["bands"]
        scale = meta["scale_factor"]
        red = img.select(bands["red"]).multiply(scale)
        nir = img.select(bands["nir"]).multiply(scale)
        swir = img.select(bands["swir1"]).multiply(scale)
        refl_valid = (red.gt(0).And(red.lt(1))
                      .And(nir.gt(0)).And(nir.lt(1))
                      .And(swir.gt(0)).And(swir.lt(1))
                      .And(nir.add(red).abs().gt(1e-6)))
        red = red.updateMask(refl_valid)
        nir = nir.updateMask(refl_valid)
        swir = swir.updateMask(refl_valid)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        wl = meta["wavelength_nm"]
        baseline = red.add(swir.subtract(red).multiply((wl["nir"] - wl["red"]) / (wl["swir1"] - wl["red"])))
        fai = nir.subtract(baseline).rename("FAI")
        qa = ee.Image.constant(30).rename("QA").toByte().updateMask(ndvi.mask())
        source = ee.Image.constant(source_value).rename("SOURCE").toByte().updateMask(ndvi.mask())
        quality = img.select("QUALITY").updateMask(ndvi.mask())
        return ndvi.addBands([fai, qa, source, quality])

    daily = []
    for key, source_value in [("MODIS_TERRA", 1), ("MODIS_AQUA", 2)]:
        meta = sensors[key]
        col = (ee.ImageCollection(meta["collection"])
               .filterBounds(roi)
               .filterDate(start, end)
               .map(lambda image: modis_mask(ee, image)))
        img = add_indices(col.median().clip(roi).updateMask(water), meta, source_value)
        daily.append(img)
    return ee.ImageCollection(daily).qualityMosaic("QUALITY").select(["NDVI", "FAI", "QA", "SOURCE", "QUALITY"]).toFloat()


def fraction_valid(ee, image, roi, water, scale):
    valid = image.select("NDVI").mask().And(water)
    stats_obj = (ee.Image.cat([
        water.rename("water"),
        valid.rename("valid")
    ]).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi,
        scale=scale,
        bestEffort=True,
        maxPixels=1e13,
        tileScale=4
    ))
    stats = get_info_with_retry(stats_obj)
    water_count = stats.get("water") or 0
    valid_count = stats.get("valid") or 0
    return float(valid_count) / float(water_count) if water_count else 0.0


def get_info_with_retry(obj, retries: int = 5):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return obj.getInfo()
        except Exception as exc:
            last_error = exc
            print(f"getInfo failed attempt {attempt}: {exc}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"getInfo failed after {retries} attempts: {last_error}")


def read_completed_coverage(path: Path, fieldnames: list[str]) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != fieldnames:
            return set()
        return {row["date"] for row in reader if row.get("date")}


def write_coverage(args):
    ee, cfg = initialize_ee()
    roi = region_geometry(ee, cfg)
    water = stable_water_mask(ee)
    out = ensure_dir(ROOT / "outputs" / "coverage") / args.coverage_output
    fieldnames = [
        "date",
        "hls_image_count",
        "hls_valid_water_fraction",
        "modis_terra_count",
        "modis_aqua_count",
        "modis_valid_water_fraction"
    ]
    completed = read_completed_coverage(out, fieldnames) if args.resume else set()
    mode = "a" if completed else "w"
    with out.open(mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not completed:
            writer.writeheader()
        for day in configured_dates(args):
            date_text = day.isoformat()
            if date_text in completed:
                print(f"coverage skip {date_text}: already complete")
                continue
            print(f"coverage {date_text}")
            hls_n = hls_count(ee, date_text, roi)
            terra_n, aqua_n = modis_counts(ee, date_text, roi)
            hls_fraction = 0.0
            if hls_n > 0:
                hls = hls_common_image(ee, date_text, roi, water)
                hls_fraction = fraction_valid(ee, hls, roi, water, 120)
            modis = modis_daily_image(ee, date_text, roi, water)
            row = {
                "date": date_text,
                "hls_image_count": hls_n,
                "hls_valid_water_fraction": hls_fraction,
                "modis_terra_count": terra_n,
                "modis_aqua_count": aqua_n,
                "modis_valid_water_fraction": fraction_valid(ee, modis, roi, water, 500)
            }
            writer.writerow(row)
            f.flush()
    print(f"Wrote {out}")


def save_response(content: bytes, target: Path):
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith((".tif", ".tiff"))]
            if len(members) != 1:
                zip_target = target.with_suffix(".zip")
                zip_target.write_bytes(content)
                return zip_target
            data = zf.read(members[0])
            target.write_bytes(data)
            return target
    target.write_bytes(content)
    return target


def download_image(ee, image, roi, out_path: Path, scale: int, crs: str, retries: int = 3):
    import requests

    params = {
        "name": out_path.stem,
        "region": roi,
        "scale": scale,
        "crs": crs,
        "format": "GEO_TIFF",
        "filePerBand": False
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            url = image.getDownloadURL(params)
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            saved = save_response(response.content, out_path)
            print(f"downloaded {saved}")
            return saved
        except Exception as exc:
            last_error = exc
            print(f"download failed {out_path.name} attempt {attempt}: {exc}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"Failed to download {out_path}: {last_error}")


def download_products(args):
    ee, cfg = initialize_ee()
    roi = region_geometry(ee, cfg)
    water = stable_water_mask(ee)
    dates = configured_dates(args)
    limit = args.max_days if args.max_days and args.max_days > 0 else None
    if limit:
        dates = dates[:limit]

    out_root = ensure_dir(ROOT / "outputs" / "rasters")
    hls_dir = ensure_dir(out_root / "hls_observed")
    modis_dir = ensure_dir(out_root / "modis_daily")
    errors = []
    for day in dates:
        date_text = day.isoformat()
        ymd = day.strftime("%Y%m%d")
        if args.product in ("modis", "all"):
            img = modis_daily_image(ee, date_text, roi, water)
            out = modis_dir / f"Taihu_MODIS_daily_NDVI_FAI_QA_{ymd}.tif"
            if not out.exists() or args.overwrite:
                try:
                    download_image(ee, img, roi, out, cfg["grid"]["modis_native_m"], cfg["grid"]["analysis_crs"])
                except Exception as exc:
                    errors.append({"date": date_text, "product": "modis", "error": repr(exc)})
        if args.product in ("hls", "all"):
            if hls_count(ee, date_text, roi) == 0:
                print(f"skip HLS {date_text}: no HLS images")
                continue
            img = hls_common_image(ee, date_text, roi, water)
            frac = fraction_valid(ee, img, roi, water, 120)
            if frac < args.min_hls_fraction:
                print(f"skip HLS {date_text}: valid fraction {frac:.3f} < {args.min_hls_fraction}")
                continue
            out = hls_dir / f"Taihu_HLS_observed_NDVI_FAI_QA_{ymd}.tif"
            if not out.exists() or args.overwrite:
                try:
                    download_image(ee, img, roi, out, cfg["grid"]["high_resolution_m"], cfg["grid"]["analysis_crs"])
                except Exception as exc:
                    errors.append({"date": date_text, "product": "hls", "error": repr(exc)})
    if errors:
        err_path = ensure_dir(ROOT / "reports") / "download_errors.json"
        err_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote errors to {err_path}")


def main():
    parser = add_common_args(argparse.ArgumentParser(description="Compute coverage and download daily Taihu NDVI/FAI products from GEE."))
    parser.add_argument("--compute-valid-coverage", action="store_true", help="Compute daily HLS/MODIS valid water fractions.")
    parser.add_argument("--download", action="store_true", help="Download daily products to outputs/rasters.")
    parser.add_argument("--product", choices=["modis", "hls", "all"], default="modis")
    parser.add_argument("--max-days", type=int, default=0, help="Limit number of dates for testing.")
    parser.add_argument("--min-hls-fraction", type=float, default=0.15, help="Minimum HLS valid water fraction for HLS download.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True, help="Resume coverage CSV when possible.")
    parser.add_argument("--coverage-output", default="daily_valid_coverage.csv", help="Coverage CSV filename under outputs/coverage.")
    args = parser.parse_args()

    if args.compute_valid_coverage:
        write_coverage(args)
    if args.download:
        download_products(args)
    if not args.compute_valid_coverage and not args.download:
        parser.print_help()


if __name__ == "__main__":
    main()
