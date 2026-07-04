from __future__ import annotations

import argparse
import csv

from common import ROOT, add_common_args, configured_dates, ensure_dir, project_config, sensor_registry


def build_plan() -> list[dict[str, object]]:
    sensors = sensor_registry()
    return [
        {"sensor": key, "collection": meta["collection"], "role": meta["role"], "native_resolution_m": meta["native_resolution_m"]}
        for key, meta in sensors.items()
    ]


def dry_run_rows(dates) -> list[dict[str, object]]:
    rows = []
    for day in dates:
        for item in build_plan():
            rows.append({
                "date": day.isoformat(),
                "sensor": item["sensor"],
                "collection": item["collection"],
                "role": item["role"],
                "native_resolution_m": item["native_resolution_m"],
                "image_count": "",
                "valid_water_fraction": "",
                "cloud_fraction": "",
                "status": "DRY_RUN"
            })
    return rows


def write_rows(rows: list[dict[str, object]]) -> None:
    out = ensure_dir(ROOT / "outputs" / "coverage") / "daily_sensor_coverage.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


def main() -> None:
    parser = add_common_args(argparse.ArgumentParser(description="Audit daily sensor coverage before exporting rasters."))
    args = parser.parse_args()
    cfg = project_config()
    dates = configured_dates(args)

    if args.dry_run:
        rows = dry_run_rows(dates)
        write_rows(rows)
        print("Dry-run only. No Earth Engine request was made.")
        return

    import ee

    ee.Initialize(project=cfg["gee_project"])
    bbox = cfg["aoi"]["bbox_wgs84"]
    roi = ee.Geometry.Rectangle(bbox)
    rows = []
    for day in dates:
        start = ee.Date(day.isoformat())
        end = start.advance(1, "day")
        for item in build_plan():
            col = ee.ImageCollection(item["collection"]).filterBounds(roi).filterDate(start, end)
            rows.append({
                "date": day.isoformat(),
                "sensor": item["sensor"],
                "collection": item["collection"],
                "role": item["role"],
                "native_resolution_m": item["native_resolution_m"],
                "image_count": col.size().getInfo(),
                "valid_water_fraction": "TODO_compute_after_AOI_mask",
                "cloud_fraction": "TODO_compute_after_sensor_QA",
                "status": "COUNTED"
            })
    write_rows(rows)


if __name__ == "__main__":
    main()

