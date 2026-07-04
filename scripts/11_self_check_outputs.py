from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


def summarize_modis_daily() -> tuple[Path, Path]:
    modis_dir = ROOT / "outputs" / "rasters" / "modis_daily"
    out_csv = ensure_dir(ROOT / "outputs" / "tables") / "modis_daily_raster_summary.csv"
    problems_path = ensure_dir(ROOT / "reports") / "modis_daily_raster_problems.json"
    rows: list[dict[str, object]] = []
    problems: list[dict[str, str]] = []

    files = sorted(modis_dir.glob("Taihu_MODIS_daily_NDVI_FAI_QA_*.tif"))
    for path in files:
        date = path.stem.split("_")[-1]
        with rasterio.open(path) as src:
            row: dict[str, object] = {
                "date": date,
                "crs": str(src.crs),
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": src.dtypes[0],
                "res_x": float(src.res[0]),
                "res_y": float(src.res[1]),
                "nodata": src.nodata,
            }
            if src.count != 5:
                problems.append({"date": date, "problem": f"band_count={src.count}"})
                rows.append(row)
                continue

            data = src.read(masked=False).astype("float64")
            ndvi, fai, qa, source, quality = data[0], data[1], data[2], data[3], data[4]
            valid = np.isfinite(ndvi) & np.isfinite(fai) & (qa > 0)

            if str(src.crs) != "EPSG:32651":
                problems.append({"date": date, "problem": f"crs={src.crs}"})
            if not (abs(src.res[0] - 500) < 1e-6 and abs(abs(src.res[1]) - 500) < 1e-6):
                problems.append({"date": date, "problem": f"res={src.res}"})
            if src.nodata == float("-inf"):
                problems.append({"date": date, "problem": "nodata_is_negative_infinity"})

            row["valid_pixels"] = int(valid.sum())
            row["valid_fraction_of_bbox_pixels"] = float(valid.mean())
            if valid.any():
                ndvi_v = ndvi[valid]
                fai_v = fai[valid]
                quality_v = quality[valid]
                source_v = source[valid].astype(int)
                row.update(
                    {
                        "ndvi_min": float(np.nanmin(ndvi_v)),
                        "ndvi_max": float(np.nanmax(ndvi_v)),
                        "ndvi_mean": float(np.nanmean(ndvi_v)),
                        "fai_min": float(np.nanmin(fai_v)),
                        "fai_max": float(np.nanmax(fai_v)),
                        "fai_mean": float(np.nanmean(fai_v)),
                        "quality_min": float(np.nanmin(quality_v)),
                        "quality_max": float(np.nanmax(quality_v)),
                        "source_terra_pixels": int((source_v == 1).sum()),
                        "source_aqua_pixels": int((source_v == 2).sum()),
                    }
                )
                row["source_other_pixels"] = (
                    int(valid.sum())
                    - int(row["source_terra_pixels"])
                    - int(row["source_aqua_pixels"])
                )
                if row["ndvi_min"] < -1.0001 or row["ndvi_max"] > 1.0001:
                    problems.append(
                        {
                            "date": date,
                            "problem": f"NDVI range {row['ndvi_min']:.3f}..{row['ndvi_max']:.3f}",
                        }
                    )
                if row["fai_min"] < -1 or row["fai_max"] > 1:
                    problems.append(
                        {
                            "date": date,
                            "problem": f"FAI range {row['fai_min']:.3f}..{row['fai_max']:.3f}",
                        }
                    )
            else:
                problems.append({"date": date, "problem": "no_QA_positive_valid_pixels"})
            rows.append(row)

    fieldnames = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    preferred = [
        "date",
        "crs",
        "width",
        "height",
        "count",
        "dtype",
        "res_x",
        "res_y",
        "valid_pixels",
        "valid_fraction_of_bbox_pixels",
        "ndvi_min",
        "ndvi_max",
        "ndvi_mean",
        "fai_min",
        "fai_max",
        "fai_mean",
        "quality_min",
        "quality_max",
        "source_terra_pixels",
        "source_aqua_pixels",
        "source_other_pixels",
        "nodata",
    ]
    fieldnames = [name for name in preferred if name in fieldnames] + [
        name for name in fieldnames if name not in preferred
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    problems_path.write_text(json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_csv, problems_path


def main() -> None:
    summary, problems = summarize_modis_daily()
    print(f"Wrote {summary}")
    print(f"Wrote {problems}")


if __name__ == "__main__":
    main()
