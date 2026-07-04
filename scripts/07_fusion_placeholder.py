from __future__ import annotations

import json


REQUIRED_FOR_REAL_FUSION = {
    "inputs": [
        "At least two high-resolution clear dates bracketing the prediction date",
        "Same-date or near-same-date coarse MODIS/Sentinel-3 evidence",
        "Coregistered rasters in a metric CRS",
        "Sensor bias correction or clear-water normalization table"
    ],
    "algorithms_to_compare": ["STARFM", "ESTARFM", "FSDAF"],
    "must_not_do": [
        "Do not call bilinear resampling STARFM",
        "Do not fuse binary bloom masks before validating reflectance/index fusion",
        "Do not mix temporal interpolation with observed pixels in one area number"
    ],
    "outputs": [
        "Predicted reflectance or FAI raster",
        "QA=20 fusion mask",
        "Source pair metadata",
        "Uncertainty or validation-derived error layer"
    ]
}


def main() -> None:
    print(json.dumps(REQUIRED_FOR_REAL_FUSION, ensure_ascii=False, indent=2))
    print("\nThis is intentionally a placeholder. Connect a tested STARFM/ESTARFM/FSDAF implementation after coverage and validation data exist.")


if __name__ == "__main__":
    main()

