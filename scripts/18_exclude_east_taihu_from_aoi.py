from __future__ import annotations

import json
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

from pyproj import Transformer  # noqa: E402
from shapely.geometry import box, mapping, shape  # noqa: E402
from shapely.ops import transform  # noqa: E402


def area_km2(geom) -> float:
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True)
    return transform(transformer.transform, geom).area / 1_000_000


def main() -> None:
    source = ROOT / "data" / "aoi" / "taihu_lake_boundary.geojson"
    target = ROOT / "data" / "aoi" / "taihu_lake_boundary_no_east_taihu.geojson"
    fc = json.loads(source.read_text(encoding="utf-8"))
    feature = fc["features"][0]
    lake = shape(feature["geometry"])

    # Approximate East Taihu exclusion box. This removes the macrophyte-dominated
    # eastern/southeastern lake area that can bias NDVI/FAI algal-bloom products.
    east_taihu_exclusion = box(120.35, 30.90, 120.95, 31.25)
    removed = lake.intersection(east_taihu_exclusion)
    kept = lake.difference(east_taihu_exclusion)

    props = feature.get("properties", {}).copy()
    props.update(
        {
            "name": "Taihu Lake excluding East Taihu",
            "source_boundary": "data/aoi/taihu_lake_boundary.geojson",
            "east_taihu_exclusion_bbox_wgs84": [120.35, 30.90, 120.95, 31.25],
            "original_area_km2_epsg32651": round(area_km2(lake), 3),
            "removed_area_km2_epsg32651": round(area_km2(removed), 3),
            "kept_area_km2_epsg32651": round(area_km2(kept), 3),
            "note": "Temporary reproducible East Taihu exclusion. Replace with a reviewed subregion boundary if available.",
        }
    )
    target.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": props, "geometry": mapping(kept)}]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = {
        "source": str(source.relative_to(ROOT)),
        "target": str(target.relative_to(ROOT)),
        "exclusion_bbox_wgs84": props["east_taihu_exclusion_bbox_wgs84"],
        "original_area_km2_epsg32651": props["original_area_km2_epsg32651"],
        "removed_area_km2_epsg32651": props["removed_area_km2_epsg32651"],
        "kept_area_km2_epsg32651": props["kept_area_km2_epsg32651"],
        "reason": "East Taihu is macrophyte/shore-complex dominated and can introduce larger NDVI/FAI errors for algal-bloom daily products.",
    }
    report_path = ensure_dir(ROOT / "reports") / "east_taihu_exclusion_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
