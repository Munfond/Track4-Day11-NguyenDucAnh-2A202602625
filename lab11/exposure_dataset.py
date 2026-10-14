"""Reproduce a data-derived exposure proxy from the four public SinD records.

Run from the lab root: python -m lab11.exposure_dataset
This independent analysis does not modify the simulator, natural prior or seeds.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.request
from pathlib import Path

import numpy as np

from .estimate import wilson_ci


CRITERIA = dict(
    unit="one observed car trajectory through the recorded intersection",
    minimum_track_duration_s=3.0,
    car_minimum_speed_mps=2.0,
    longitudinal_closing_speed_min_mps=0.1,
    bicycle_speed_mps=[2.8, 4.4],
    initial_longitudinal_distance_m=[10.0, 18.0],
    initial_absolute_lateral_distance_m=[1.6, 4.5],
    initial_heading_difference_max_deg=30.0,
    car_heading_change_max_deg=15.0,
    car_lateral_drift_max_m=0.5,
    observation_window_s=2.6,
    final_absolute_lateral_distance_max_m=1.6,
    lateral_approach_min_m=1.0,
    deduplication="at most one positive outcome per eligible car track",
)


def load_tracks(path):
    tracks = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            kind = row["agent_type"]
            if kind not in ("car", "bicycle"):
                continue
            key = (kind, int(row["track_id"]))
            # time, frame, x, y, vx, vy, car-body heading
            tracks.setdefault(key, []).append([
                float(row["timestamp_ms"]) / 1000, int(row["frame_id"]),
                float(row["x"]), float(row["y"]),
                float(row["vx"]), float(row["vy"]), float(row["yaw_rad"]),
            ])
    return {key: np.asarray(sorted(rows), dtype=float) for key, rows in tracks.items()}


def find_encounter(car, bike, longitudinal=(10.0, 18.0)):
    """First same-direction bicycle intrusion under fixed, declared criteria."""
    _, ci, bi = np.intersect1d(car[:, 1], bike[:, 1], return_indices=True)
    if len(ci) < 2:
        return None
    c, b = car[ci], bike[bi]
    heading = c[:, 6]
    hx, hy = np.cos(heading), np.sin(heading)
    rx, ry = b[:, 2] - c[:, 2], b[:, 3] - c[:, 3]
    lon = rx * hx + ry * hy
    lat = -rx * hy + ry * hx
    cv = np.hypot(c[:, 4], c[:, 5])
    bv = np.hypot(b[:, 4], b[:, 5])
    same_direction = np.sum(c[:, 4:6] * b[:, 4:6], axis=1) / np.maximum(cv * bv, 1e-12)
    closing = (c[:, 4] - b[:, 4]) * hx + (c[:, 5] - b[:, 5]) * hy
    candidates = np.flatnonzero(
        (cv >= 2.0) & (bv >= 2.8) & (bv <= 4.4)
        & (closing > 0.1)
        & (lon >= longitudinal[0]) & (lon <= longitudinal[1])
        & (np.abs(lat) > 1.6) & (np.abs(lat) <= 4.5)
        & (same_direction >= math.cos(math.radians(30)))
    )
    for start in candidates:
        t0 = c[start, 0]
        end = int(np.searchsorted(c[:, 0], t0 + 2.6, side="right"))
        if end <= start + 1 or c[end - 1, 0] - t0 < 2.5:
            continue  # no full observation window near track boundaries
        cc, bb = c[start:end], b[start:end]
        if np.max(np.diff(cc[:, 0])) > 0.15:
            continue
        dh = np.arctan2(np.sin(cc[:, 6] - heading[start]), np.cos(cc[:, 6] - heading[start]))
        if np.max(np.abs(dh)) > math.radians(15):
            continue  # exclude a car turning into a bicycle instead of a bicycle intrusion
        dx, dy = cc[:, 2] - cc[0, 2], cc[:, 3] - cc[0, 3]
        car_drift = -dx * hy[start] + dy * hx[start]
        if np.max(np.abs(car_drift)) > 0.5:
            continue
        rel = bb[:, 2:4] - cc[:, 2:4]
        future_lat = -rel[:, 0] * hy[start] + rel[:, 1] * hx[start]
        future_lon = rel[:, 0] * hx[start] + rel[:, 1] * hy[start]
        entry = np.flatnonzero(
            (np.abs(future_lat) <= 1.6)
            & (np.abs(lat[start]) - np.abs(future_lat) >= 1.0)
            & (future_lon > 0)
        )
        if not len(entry):
            continue
        j = int(entry[0])
        return dict(
            start_time_s=float(t0), entry_time_s=float(cc[j, 0]),
            start_frame=int(cc[0, 1]), entry_frame=int(cc[j, 1]),
            initial_lon_m=float(lon[start]), initial_lat_m=float(lat[start]),
            entry_lon_m=float(future_lon[j]), entry_lat_m=float(future_lat[j]),
            bicycle_speed_mps=float(bv[start]), car_speed_mps=float(cv[start]),
            longitudinal_closing_speed_mps=float(closing[start]),
            car_heading_change_max_deg=float(np.degrees(np.max(np.abs(dh)))),
            car_lateral_drift_max_m=float(np.max(np.abs(car_drift))),
            samples=[dict(t=float(x[0]), car_xy=x[2:4].tolist(), bike_xy=y[2:4].tolist())
                     for x, y in zip(cc, bb)],
        )
    return None


def analyse(folder):
    folder = Path(folder)
    tracks = load_tracks(folder / "Veh_smoothed_tracks.csv")
    cars = {i: t for (kind, i), t in tracks.items()
            if kind == "car" and t[-1, 0] - t[0, 0] >= 3.0}
    bikes = {i: t for (kind, i), t in tracks.items() if kind == "bicycle"}
    events = []
    sensitivity = {}
    for label, band in (("primary", (10, 18)), ("narrow", (12, 16)), ("wide", (8, 22))):
        hit_ids = set()
        for car_id, c in cars.items():
            for bike_id, b in bikes.items():
                if b[-1, 0] < c[0, 0] or b[0, 0] > c[-1, 0]:
                    continue
                event = find_encounter(c, b, band)
                if event is not None:
                    hit_ids.add(car_id)
                    if label == "primary":
                        events.append(dict(car_id=car_id, bicycle_id=bike_id, **event))
                    break
        k, n = len(hit_ids), len(cars)
        lo, hi = wilson_ci(k, n)
        sensitivity[label] = dict(longitudinal_band_m=list(band), k=k, n=n,
                                  p=k / n if n else None, wilson_lo=lo, wilson_hi=hi,
                                  positive_car_ids=sorted(hit_ids))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        data = (folder / Path(entry["path"]).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Dataset checksum changed: " + entry["path"])
    return dict(
        dataset=manifest["dataset"], repository=manifest["repository"], commit=manifest["commit"],
        criteria=CRITERIA, total_car_tracks=sum(kind == "car" for kind, _ in tracks),
        total_bicycle_tracks=len(bikes), eligible_car_ids=sorted(cars),
        result=sensitivity["primary"], sensitivity=sensitivity, events=events,
        interpretation="Empirical local encounter proxy per eligible car passage, not whole-journey exposure. "
                       "A sample record at a Chinese intersection is not a calibrated frequency for the lab town. "
                       "The event detects an observed intrusion, not all exact synthetic swerve parameters. "
                       "Wilson limits are nominal under independent Bernoulli passages; shared traffic and sample selection limit generalisation.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="evidence/exposure_dataset")
    parser.add_argument("--output", default="evidence/exposure.json")
    parser.add_argument("--download", action="store_true",
                        help="Fetch missing raw CSVs from the fixed URLs in the source manifests")
    args = parser.parse_args()
    folder = Path(args.data)
    folders = [folder] + sorted(p for p in folder.iterdir()
                               if p.is_dir() and (p / "manifest.json").exists())
    if args.download:
        for source in folders:
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            for entry in manifest["files"]:
                target = source / Path(entry["path"]).name
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
                    continue
                request = urllib.request.Request(entry["url"], headers={"User-Agent": "Lab11-exposure-research"})
                data = urllib.request.urlopen(request, timeout=30).read()
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise ValueError("Downloaded dataset checksum mismatch: " + entry["path"])
                target.write_bytes(data)
    records = [analyse(p) for p in folders]
    result = records[0] if len(records) == 1 else dict(
        dataset=f"All {len(records)} publicly available SinD sample records at the fixed repository commit",
        repository=records[0]["repository"], commit=records[0]["commit"],
        criteria=CRITERIA, records=records, sensitivity={},
        interpretation=records[0]["interpretation"],
    )
    if len(records) > 1:
        for label in ("primary", "narrow", "wide"):
            k = sum(r["sensitivity"][label]["k"] for r in records)
            n = sum(r["sensitivity"][label]["n"] for r in records)
            lo, hi = wilson_ci(k, n)
            result["sensitivity"][label] = dict(
                longitudinal_band_m=records[0]["sensitivity"][label]["longitudinal_band_m"],
                k=k, n=n, p=k / n if n else None, wilson_lo=lo, wilson_hi=hi,
            )
        result["result"] = result["sensitivity"]["primary"]
        result["total_car_tracks"] = sum(r["total_car_tracks"] for r in records)
        result["total_bicycle_tracks"] = sum(r["total_bicycle_tracks"] for r in records)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "sensitivity": result["sensitivity"],
                      "total_car_tracks": result["total_car_tracks"],
                      "total_bicycle_tracks": result["total_bicycle_tracks"]}, indent=2))


if __name__ == "__main__":
    main()
