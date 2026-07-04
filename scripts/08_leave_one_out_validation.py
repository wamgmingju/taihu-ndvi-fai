from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import ROOT, ensure_dir

import numpy as np


def binary_metrics(truth: np.ndarray, pred: np.ndarray, threshold: float) -> dict[str, float]:
    valid = np.isfinite(truth) & np.isfinite(pred)
    if valid.sum() == 0:
        return {"rmse": float("nan"), "mae": float("nan"), "iou": float("nan"), "f1": float("nan")}
    err = pred[valid] - truth[valid]
    truth_b = truth[valid] > threshold
    pred_b = pred[valid] > threshold
    tp = np.logical_and(truth_b, pred_b).sum()
    fp = np.logical_and(~truth_b, pred_b).sum()
    fn = np.logical_and(truth_b, ~pred_b).sum()
    iou = tp / max(tp + fp + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mae": float(np.mean(np.abs(err))),
        "iou": float(iou),
        "f1": float(f1)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare held-out high-resolution FAI with a predicted FAI raster.")
    parser.add_argument("--truth", help="Held-out high-resolution FAI GeoTIFF.")
    parser.add_argument("--prediction", help="Predicted fusion FAI GeoTIFF.")
    parser.add_argument("--threshold", type=float, default=0.05, help="FAI threshold for binary bloom metrics.")
    args = parser.parse_args()
    if not args.truth or not args.prediction:
        print("Provide --truth and --prediction after fusion outputs exist.")
        return

    import rasterio

    with rasterio.open(args.truth) as src:
        truth = src.read(1).astype("float64")
        if src.nodata is not None:
            truth[truth == src.nodata] = np.nan
    with rasterio.open(args.prediction) as src:
        pred = src.read(1).astype("float64")
        if src.nodata is not None:
            pred[pred == src.nodata] = np.nan
    metrics = binary_metrics(truth, pred, args.threshold)
    out = ensure_dir(ROOT / "outputs" / "tables") / "leave_one_out_validation.csv"
    exists = Path(out).exists()
    with out.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["truth", "prediction", "threshold", *metrics.keys()])
        if not exists:
            writer.writeheader()
        writer.writerow({"truth": args.truth, "prediction": args.prediction, "threshold": args.threshold, **metrics})
    print(metrics)
    print(f"Updated {out}")


if __name__ == "__main__":
    main()
