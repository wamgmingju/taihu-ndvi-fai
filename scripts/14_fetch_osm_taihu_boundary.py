from __future__ import annotations

import json
import sys
from pathlib import Path

from common import LOCAL_PYLIBS, ROOT, ensure_dir

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))

import requests  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import LineString, mapping, shape  # noqa: E402
from shapely.ops import polygonize, transform, unary_union  # noqa: E402


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TAIHU_RELATION_ID = 1126533


def fetch_relation() -> dict:
    query = f"""[out:json][timeout:120];
rel({TAIHU_RELATION_ID}); out body;
way(r); out body geom;"""
    response = requests.post(
        OVERPASS_URL,
        data=query.encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "taihu-ndvi-fai-codex",
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def relation_to_polygon(osm: dict):
    relation = next(e for e in osm["elements"] if e["type"] == "relation")
    ways = {e["id"]: e for e in osm["elements"] if e["type"] == "way"}
    outer_lines = []
    inner_lines = []
    for member in relation["members"]:
        if member.get("type") != "way" or member.get("ref") not in ways:
            continue
        geom = ways[member["ref"]].get("geometry") or []
        if len(geom) < 2:
            continue
        coords = [(p["lon"], p["lat"]) for p in geom]
        line = LineString(coords)
        if member.get("role") == "inner":
            inner_lines.append(line)
        else:
            outer_lines.append(line)

    outer_polys = list(polygonize(outer_lines))
    if not outer_polys:
        raise RuntimeError("Could not polygonize OSM outer ways.")
    outer = unary_union(outer_polys)

    inner_polys = list(polygonize(inner_lines))
    if inner_polys:
        outer = outer.difference(unary_union(inner_polys))
    return outer


def area_km2_wgs84(geom) -> float:
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True)
    projected = transform(transformer.transform, geom)
    return projected.area / 1_000_000


def main() -> None:
    osm = fetch_relation()
    polygon = relation_to_polygon(osm)
    relation = next(e for e in osm["elements"] if e["type"] == "relation")
    props = relation.get("tags", {}).copy()
    props.update(
        {
            "name": "Taihu Lake",
            "name_zh": "Taihu",
            "source": "OpenStreetMap Overpass API",
            "osm_relation_id": TAIHU_RELATION_ID,
            "area_km2_epsg32651": round(area_km2_wgs84(polygon), 3),
            "boundary_status": "temporary reproducible lake boundary; replace with official Taihu boundary if available",
        }
    )
    feature = {"type": "Feature", "properties": props, "geometry": mapping(polygon)}
    out = ensure_dir(ROOT / "data" / "aoi") / "taihu_lake_boundary.geojson"
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": [feature]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "output": "data/aoi/taihu_lake_boundary.geojson",
        "source": OVERPASS_URL,
        "osm_relation_id": TAIHU_RELATION_ID,
        "selected_name": "Taihu Lake",
        "selected_name_en": props.get("name:en"),
        "area_km2_epsg32651": props["area_km2_epsg32651"],
        "ways_total": len([e for e in osm["elements"] if e["type"] == "way"]),
        "note": props["boundary_status"],
    }
    report_path = ensure_dir(ROOT / "reports") / "aoi_boundary_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
