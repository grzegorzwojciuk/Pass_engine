import argparse
from .models import Observer
from datetime import datetime, UTC
from pathlib import Path
from .tle import load_tle, TleError
from .orbit import find_passes, elevation_track
import json
import csv
import sys
import time
from math import ceil

def main(argv = None):
    args = build_parser().parse_args(argv)
    lat_deg, lon_deg, alt_m = args.location
    observer = Observer(lat_deg, lon_deg, alt_m, min_elev_deg=args.min_elev)
    start = args.start if args.start is not None else datetime.now(UTC)
    days = args.days
    try:
        records = sorted(
                    load_tle(args.tle),
                    key=lambda record: record.epoch,
                    reverse=True,
                        )
    except (OSError, TleError) as error:
        print(error, file=sys.stderr)
        return 2
    selected_records = {}
    for record in records:
        if (record.satellite_number not in selected_records) or (abs((record.epoch - start).total_seconds()) < abs((selected_records[record.satellite_number].epoch - start).total_seconds())):
            selected_records[record.satellite_number] = record
    if args.satnum == "all":
        records_to_process = list(selected_records.values())
    else: 
        try:
            satnum = int(args.satnum)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        if satnum not in selected_records:
            print("Given satellite number is not in any TLE.", file=sys.stderr)
            return 2
        else:
            records_to_process = [selected_records[satnum]]
    passes_with_records = []
    try:
        for record in records_to_process:
            record_passes = find_passes(record, observer, start, days)
            for pass_info in record_passes:
                passes_with_records.append((pass_info, record))
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    passes_with_records.sort(key=lambda item: item[0].aos)
    passes = [pass_info for pass_info, record in passes_with_records]
    if args.command == "next":
        if not passes:
            print("No passes.", file=sys.stderr)
            return 2
        next_pass = passes[0]
        seconds_to_aos = (next_pass.aos - start).total_seconds()
        if args.format in ("json", "csv"):
            row = {
                "satellite": next_pass.satellite,
                "aos": next_pass.aos.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "los": next_pass.los.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "max_elev_deg": next_pass.max_elev_deg,
                "max_elev_time": next_pass.max_elev_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "az_aos_deg": next_pass.az_aos_deg,
                "az_los_deg": next_pass.az_los_deg,
                "duration_s": next_pass.duration_s
            }
            if args.format == "json":
                print(json.dumps({"pass": row, "seconds_to_aos": seconds_to_aos}))
            else:
                row["seconds_to_aos"] = seconds_to_aos
                columns = (
                    "satellite", "aos", "los",
                    "max_elev_deg", "max_elev_time",
                    "az_aos_deg", "az_los_deg",
                    "duration_s", "seconds_to_aos"
                    )
                writer = csv.DictWriter(sys.stdout, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerow(row)
        else: 
            aos = next_pass.aos
            los = next_pass.los
            max_elev_deg = next_pass.max_elev_deg
            duration_s = next_pass.duration_s 
            az_aos_deg = next_pass.az_aos_deg
            az_los_deg = next_pass.az_los_deg
            aos_text = aos.isoformat(timespec="seconds").replace("+00:00", "Z")
            los_text = los.isoformat(timespec="seconds").replace("+00:00", "Z")
            max_elev_deg_text = f"{max_elev_deg:.1f}"
            az_aos_deg_text = f"{az_aos_deg:.1f}"
            az_los_deg_text = f"{az_los_deg:.1f}"
            duration_s_text = f"{duration_s:.1f}"
            hours, remainder = divmod(int(seconds_to_aos), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_to_aos_text = f"{hours} h {minutes} min {seconds} s"
            print("AOS (UTC) | LOS (UTC) | Max el | Duration (s) | Az AOS -> LOS | Time to AOS")
            print(aos_text, "|", los_text, "|", max_elev_deg_text, "|", duration_s_text, "|", az_aos_deg_text, " -> ", az_los_deg_text, "|", time_to_aos_text)
        remaining = (next_pass.aos - datetime.now(UTC)).total_seconds()
        if args.countdown == True and 0 < remaining <= 60:
            try:
                while 0 < remaining <= 60:
                    print(ceil(remaining), file=sys.stderr, flush=True)
                    time.sleep(min(1.0, remaining))
                    remaining = (next_pass.aos - datetime.now(UTC)).total_seconds()
            except KeyboardInterrupt:
                return 0
        return 0
    elif args.command == "list":
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
    elif args.command == "show":
        if not (1<= args.id <= len(passes)):
            print("Given id out of range.", file=sys.stderr)
            return 2
        selected_pass, selected_record = passes_with_records[args.id - 1]
        try:
            track = elevation_track(
                selected_record, observer,
                selected_pass.aos, selected_pass.los,
                step_s=args.step,
                )
        except (ValueError, RuntimeError) as error:
            print(error, file=sys.stderr)
            return 2
        pass_dict = {
            "satellite": selected_pass.satellite,
            "aos": selected_pass.aos.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "los": selected_pass.los.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "max_elev_deg": selected_pass.max_elev_deg,
            "max_elev_time": selected_pass.max_elev_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "az_aos_deg": selected_pass.az_aos_deg,
            "az_los_deg": selected_pass.az_los_deg,
            "duration_s": selected_pass.duration_s            
        }
        if args.format in ("json", "csv"):
            track_rows = []
            for sample_time, elevation_deg, azimuth_deg in track:
                pass_row = {
                    "time_utc": sample_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "elevation_deg": elevation_deg,
                    "azimuth_deg": azimuth_deg
                }
                track_rows.append(pass_row)
            
            if args.format == "json":
                print(json.dumps({"pass": pass_dict, "track": track_rows}))
                return 0
            else:
                columns = ("time_utc", "elevation_deg", "azimuth_deg")
                writer = csv.DictWriter(sys.stdout, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerows(track_rows)
                return 0
        else:
            print("# | Satellite | AOS (UTC) | LOS (UTC) | Max el (deg) | Max time (UTC) | Duration (s) | Az AOS -> LOS")
            print(
                args.id, "|", pass_dict["satellite"], "|",
                pass_dict["aos"], "|", pass_dict["los"], "|",
                f"{pass_dict['max_elev_deg']:.1f}", "|",
                pass_dict["max_elev_time"], "|",
                f"{pass_dict['duration_s']:.1f}", "|",
                f"{pass_dict['az_aos_deg']:.1f}", "->",
                f"{pass_dict['az_los_deg']:.1f}"
                )
            print(f"PASS {args.id}:")
            print("TIME (UTC) | ELEVATION (DEG) | AZIMUTH (DEG)")
            for sample_time, elevation_deg, azimuth_deg in track:
                print(
                    sample_time.isoformat(timespec="seconds").replace("+00:00", "Z"), "|",
                    f"{elevation_deg:.1f}", "|", f"{azimuth_deg:.1f}"
                    )
            return 0



def build_parser():
   parser = argparse.ArgumentParser(prog="pass_engine")
   subparsers = parser.add_subparsers(dest="command", required=True)
   list_parser = subparsers.add_parser("list")
   next_parser = subparsers.add_parser("next")
   show_parser = subparsers.add_parser("show")
   default_satnum = 99999 # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< DEFAULT SATELLITE NUMBER
   for command_parser in (list_parser, next_parser, show_parser):
        command_parser.add_argument("--tle", required=True, type=Path)
        command_parser.add_argument("--location", required=True, type=parse_location)
        command_parser.add_argument("--min-elev", type=float, default=10.0)
        command_parser.add_argument("--start", type=parse_start)
        command_parser.add_argument("--days", type=float, default=7.0)
        command_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
        command_parser.add_argument("--satnum", default=str(default_satnum))
   next_parser.add_argument("--countdown", action="store_true")
   show_parser.add_argument("--id", type=int, required=True)
   show_parser.add_argument("--step", type=float, default=30.0)
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