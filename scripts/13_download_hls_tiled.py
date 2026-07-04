from __future__ import annotations

import argparse
import importlib.util
import io
import sys
import time
import zipfile
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, configured_dates, ensure_dir, project_config

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import requests  # noqa: E402
from rasterio.merge import merge  # noqa: E402


def load_daily_module():
    path = ROOT / "scripts" / "10_gee_process_daily.py"
    spec = importlib.util.spec_from_file_location("gee_daily", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grid_from_bbox(bbox: list[float], nx: int, ny: int) -> list[tuple[int, list[float]]]:
    xmin, ymin, xmax, ymax = bbox
    dx = (xmax - xmin) / nx
    dy = (ymax - ymin) / ny
    tiles: list[tuple[int, list[float]]] = []
    idx = 0
    for iy in range(ny):
        for ix in range(nx):
            idx += 1
            tiles.append(
                (
                    idx,
                    [
                        xmin + ix * dx,
                        ymin + iy * dy,
                        xmin + (ix + 1) * dx,
                        ymin + (iy + 1) * dy,
                    ],
                )
            )
    return tiles


def save_response(content: bytes, target: Path) -> Path:
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith((".tif", ".tiff"))]
            if len(members) != 1:
                zip_target = target.with_suffix(".zip")
                zip_target.write_bytes(content)
                return zip_target
            target.write_bytes(zf.read(members[0]))
            return target
    target.write_bytes(content)
    return target


def normalize_nodata(path: Path, nodata: float = -9999.0) -> None:
    with rasterio.open(path) as src:
        data = src.read(masked=False).astype("float32", copy=False)
        profile = src.profile.copy()
    data[~np.isfinite(data)] = nodata
    profile.update(dtype="float32", nodata=nodata, compress="DEFLATE", predictor=2)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(data)
    tmp.replace(path)


def download_tile(ee, image, tile_bbox: list[float], out_path: Path, scale: int, crs: str, retries: int = 5) -> Path:
    region = ee.Geometry.Rectangle(tile_bbox)
    params = {
        "name": out_path.stem,
        "region": region,
        "scale": scale,
        "crs": crs,
        "format": "GEO_TIFF",
        "filePerBand": False,
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            url = image.getDownloadURL(params)
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            saved = save_response(response.content, out_path)
            normalize_nodata(saved)
            return saved
        except Exception as exc:
            last_error = exc
            print(f"tile failed {out_path.name} attempt {attempt}: {exc}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"Failed tile {out_path}: {last_error}")


def mosaic_tiles(tile_paths: list[Path], output: Path, nodata: float = -9999.0) -> None:
    datasets = [rasterio.open(path) for path in tile_paths]
    try:
        mosaic, transform = merge(datasets, nodata=nodata)
        profile = datasets[0].profile.copy()
        profile.update(
            height=mosaic.shape[1],
            width=mosaic.shape[2],
            transform=transform,
            nodata=nodata,
            dtype="float32",
            compress="DEFLATE",
            predictor=2,
        )
    finally:
        for ds in datasets:
            ds.close()
    tmp = output.with_suffix(output.suffix + ".tmp")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(mosaic.astype("float32", copy=False))
    tmp.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download HLS observed NDVI/FAI products with tiled getDownloadURL requests.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--min-hls-fraction", type=float, default=0.15)
    parser.add_argument("--nx", type=int, default=4)
    parser.add_argument("--ny", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--keep-tiles", action="store_true")
    parser.add_argument("--output-dir", default="hls_observed")
    parser.add_argument("--tile-dir", default="hls_tiles")
    args = parser.parse_args()

    daily = load_daily_module()
    ee, cfg = daily.initialize_ee()
    roi = daily.region_geometry(ee, cfg)
    water = daily.stable_water_mask(ee)
    dates = configured_dates(args)

    out_dir = ensure_dir(ROOT / "outputs" / "rasters" / args.output_dir)
    tile_root = ensure_dir(ROOT / "outputs" / "rasters" / args.tile_dir)
    tiles = grid_from_bbox(cfg["aoi"]["bbox_wgs84"], args.nx, args.ny)

    for day in dates:
        date_text = day.isoformat()
        ymd = day.strftime("%Y%m%d")
        output = out_dir / f"Taihu_HLS_observed_NDVI_FAI_QA_{ymd}.tif"
        if output.exists() and not args.overwrite:
            print(f"skip {date_text}: output exists")
            continue
        if daily.hls_count(ee, date_text, roi) == 0:
            print(f"skip {date_text}: no HLS images")
            continue
        image = daily.hls_common_image(ee, date_text, roi, water)
        fraction = daily.fraction_valid(ee, image, roi, water, 120)
        if fraction < args.min_hls_fraction:
            print(f"skip {date_text}: valid fraction {fraction:.3f} < {args.min_hls_fraction}")
            continue

        day_tile_dir = ensure_dir(tile_root / ymd)
        tile_paths: list[Path] = []
        print(f"download HLS {date_text}: valid fraction={fraction:.3f}, tiles={len(tiles)}")
        for tile_id, tile_bbox in tiles:
            tile_path = day_tile_dir / f"Taihu_HLS_{ymd}_tile_{tile_id:02d}.tif"
            if not tile_path.exists() or args.overwrite:
                print(f"  tile {tile_id:02d}/{len(tiles)}")
                download_tile(
                    ee,
                    image,
                    tile_bbox,
                    tile_path,
                    cfg["grid"]["high_resolution_m"],
                    cfg["grid"]["analysis_crs"],
                )
            tile_paths.append(tile_path)
        mosaic_tiles(tile_paths, output)
        print(f"wrote {output}")

        if not args.keep_tiles:
            for tile_path in tile_paths:
                tile_path.unlink(missing_ok=True)
            day_tile_dir.rmdir()


if __name__ == "__main__":
    main()
