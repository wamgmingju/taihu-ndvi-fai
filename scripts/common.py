from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"
LOCAL_PYLIBS = ROOT.parents[1] / "pylibs"

if LOCAL_PYLIBS.exists() and str(LOCAL_PYLIBS) not in sys.path:
    sys.path.insert(0, str(LOCAL_PYLIBS))


def load_json(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def project_config() -> dict[str, Any]:
    return load_json("project_config.json")


def sensor_registry() -> dict[str, Any]:
    return load_json("sensor_registry.json")


def qa_codes() -> dict[str, Any]:
    return load_json("qa_codes.json")


def date_range(start: str, end: str) -> list[dt.date]:
    begin = dt.date.fromisoformat(start)
    finish = dt.date.fromisoformat(end)
    days = (finish - begin).days
    return [begin + dt.timedelta(days=i) for i in range(days + 1)]


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--dry-run", action="store_true", help="Print planned work without starting exports.")
    parser.add_argument("--start", help="Override start date YYYY-MM-DD.")
    parser.add_argument("--end", help="Override end date YYYY-MM-DD.")
    return parser


def configured_dates(args: argparse.Namespace) -> list[dt.date]:
    cfg = project_config()
    start = args.start or cfg["date_range"]["start"]
    end = args.end or cfg["date_range"]["end"]
    return date_range(start, end)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def fai(red, nir, swir, wavelengths: dict[str, float]):
    red_l = wavelengths["red"]
    nir_l = wavelengths["nir"]
    swir_l = wavelengths["swir1"]
    baseline = red + (swir - red) * ((nir_l - red_l) / (swir_l - red_l))
    return nir - baseline


def ndvi(red, nir):
    return (nir - red) / (nir + red + 1e-8)


def mndwi(green, swir):
    return (green - swir) / (green + swir + 1e-8)
