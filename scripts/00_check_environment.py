from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path

from common import ROOT, ensure_dir, project_config, sensor_registry


MODULES = ["ee", "numpy", "pandas", "rasterio", "geopandas", "pyproj", "shapely"]


def module_status(name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(name)
    status = {"available": spec is not None, "version": None}
    if spec is not None:
        try:
            module = importlib.import_module(name)
            status["version"] = getattr(module, "__version__", "unknown")
        except Exception as exc:
            status["available"] = False
            status["error"] = repr(exc)
    return status


def main() -> None:
    cfg = project_config()
    sensors = sensor_registry()
    report = {
        "python": sys.version,
        "platform": platform.platform(),
        "root": str(ROOT),
        "date_range": cfg["date_range"],
        "analysis_crs": cfg["grid"]["analysis_crs"],
        "sensor_count": len(sensors),
        "modules": {name: module_status(name) for name in MODULES},
        "aoi_files": {
            "lake_boundary_exists": (ROOT / cfg["aoi"]["preferred_vector"]).exists(),
            "subregions_exists": (ROOT / cfg["aoi"]["subregions_vector"]).exists()
        }
    }
    out = ensure_dir(ROOT / "reports") / "environment_check.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

