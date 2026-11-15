import argparse
from .models import Observer
from datetime import datetime, UTC
from pathlib import Path
from .tle import load_tle
from .orbit import find_passes
import json
import csv
import sys

def main(argv = None):
    args = build_parser().parse_args(argv)
    lat_deg, lon_deg, alt_m = args.location
    observer = Observer(lat_deg, lon_deg, alt_m, min_elev_deg=args.min_elev)
    start = args.start if args.start is not None else datetime.now(UTC)
    days = args.days
    records = load_tle(args.tle)
    passes = find_passes(records[0], observer, start, days)
    if args.format in ("json", "csv"):
        rows = []
        counter = 1
        for i in passes:
            pass_dict = {
                "index": counter,
                "satellite": i.satellite,
                "aos": i.aos.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "los": i.los.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "max_elev_deg": i.max_elev_deg,
                "max_elev_time": i.max_elev_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "az_aos_deg": i.az_aos_deg,
                "az_los_deg": i.az_los_deg,
                "duration_s": i.duration_s
                }
            rows.append(pass_dict)
            counter = counter + 1
        if args.format == "json":
            print(json.dumps(rows))
            return 0
        else:
            columns = (
                "index", "satellite", "aos", "los",
                "max_elev_deg", "max_elev_time",
                "az_aos_deg", "az_los_deg", "duration_s",
                )
            writer = csv.DictWriter(sys.stdout, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            return 0

    else:
        if not passes:
            print("No passes.")
            return 0
        else:
            index = 1
            print("# | AOS (UTC) | LOS (UTC) | Max el | Duration (s) | Az AOS -> LOS")
            for i in passes:
                aos = i.aos
                los = i.los
                max_elev_deg = i.max_elev_deg
                duration_s = i.duration_s 
                az_aos_deg = i.az_aos_deg
                az_los_deg = i.az_los_deg
                aos_text = aos.isoformat(timespec="seconds").replace("+00:00", "Z")
                los_text = los.isoformat(timespec="seconds").replace("+00:00", "Z")
                max_elev_deg_text = f"{max_elev_deg:.1f}"
                az_aos_deg_text = f"{az_aos_deg:.1f}"
                az_los_deg_text = f"{az_los_deg:.1f}"
                duration_s_text = f"{duration_s:.1f}"
                print(index, "|", aos_text, "|", los_text, "|", max_elev_deg_text, "|", duration_s_text, "|", az_aos_deg_text, " -> ", az_los_deg_text)
                index = index + 1
        return 0


def build_parser():
   parser = argparse.ArgumentParser(prog="pass_engine")
   subparsers = parser.add_subparsers(dest="command", required=True)
   list_parser = subparsers.add_parser("list")
   next_parser = subparsers.add_parser("next")
   for command_parser in (list_parser, next_parser):
        command_parser.add_argument("--tle", required=True, type=Path)
        command_parser.add_argument("--location", required=True, type=parse_location)
        command_parser.add_argument("--min-elev", type=float, default=10.0)
        command_parser.add_argument("--start", type=parse_start)
        command_parser.add_argument("--days", type=float, default=7.0)
        command_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
   
   return parser

def parse_location(location: str) -> tuple[float, float, float]:
    location = location.split(",")
    if len(location) not in [2, 3]:
        raise ValueError ("Inapropriate location format.")
    lat_deg = float(location[0])
    if not (-90 <= lat_deg <= 90):
        raise ValueError ("Latitude out of range.")         #Use '=' for negative latitude (--location =...)
    lon_deg = float(location[1])
    if not (-180 <= lon_deg <= 180):
        raise ValueError ("Longitude out of range.")
    if len(location) == 3:
        alt_m = float(location[2])
    else:
        alt_m = 0.0

    return (lat_deg, lon_deg, alt_m)

def parse_start(text: str) -> datetime:
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("No timezone given.")
    return dt.astimezone(UTC)