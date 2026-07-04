from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from common import ROOT, ensure_dir, project_config


def load_daily_module():
    path = ROOT / "scripts" / "10_gee_process_daily.py"
    spec = importlib.util.spec_from_file_location("gee_daily", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    daily = load_daily_module()
    ee, cfg = daily.initialize_ee()
    bbox = cfg["aoi"]["bbox_wgs84"]
    search_region = ee.Geometry.Rectangle(bbox)
    collection = ee.FeatureCollection("projects/sat-io/open-datasets/HydroLakes/lake_poly_v10")
    candidates = collection.filterBounds(search_region).filter(ee.Filter.gt("Lake_area", 500))
    features = daily.get_info_with_retry(candidates.sort("Lake_area", False).limit(10))
    if not features.get("features"):
        raise RuntimeError("No HydroLAKES candidate larger than 500 km2 found in AOI bbox.")

    selected = features["features"][0]
    out = ensure_dir(ROOT / "data" / "aoi") / "taihu_lake_boundary.geojson"
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": [selected]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    props = selected.get("properties", {})
    report = {
        "source": "HydroLAKES v1.0 via GEE community catalog",
        "asset": "projects/sat-io/open-datasets/HydroLakes/lake_poly_v10",
        "selection_rule": "filter AOI bbox, Lake_area > 500 km2, choose largest Lake_area",
        "output": str(out),
        "selected_properties": props,
        "candidate_count_returned": len(features["features"]),
    }
    report_path = ensure_dir(ROOT / "reports") / "aoi_boundary_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {report_path}")
    print(json.dumps(props, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
