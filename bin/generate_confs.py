#!/usr/bin/env python3
"""
Generate FS42 confs by scanning FieldStation42/catalog/.
- No hard-coded channels.
- ONLY 'movies' and 'shows' tags in schedules.
- Channel numbers are persisted and stable in confs/.channel_map.json
- Avoids channel numbers 80–89.
"""

import os, json, argparse, random
from pathlib import Path

# Where the main repo lives (catalog/ and confs/)
DEFAULT_FSROOT = Path("/mnt/media01/projects/FieldStation42")

def resolve_fsroot(cli_fsroot: str | None) -> Path:
    if cli_fsroot:
        return Path(cli_fsroot).resolve()
    env = os.getenv("FS42_ROOT")
    return Path(env).resolve() if env else DEFAULT_FSROOT

VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".ts", ".webm", ".m4v"}
RESERVED = set(range(80, 90))  # never use 80–89

def pretty_name(name: str) -> str:
    parts = name.replace("_"," ").replace("-"," ").split()
    return "".join(p.capitalize() for p in parts) if parts else name

def has_videos(p: Path) -> bool:
    if not p.is_dir():
        return False
    for root, _, files in os.walk(p):
        for f in files:
            if Path(f).suffix.lower() in VIDEO_EXT:
                return True
    return False

def classify(chan_dir: Path) -> str:
    """Return 'movies', 'shows', 'mixed', or 'empty' based on subfolders."""
    has_movies = has_videos(chan_dir / "movies")
    has_shows  = has_videos(chan_dir / "shows")
    if has_movies and has_shows: return "mixed"
    if has_movies: return "movies"
    if has_shows:  return "shows"
    return "empty"

def weekly_schedule(kind: str) -> dict:
    """
    Build a 7-day schedule with ONLY 'movies' and 'shows'.
    - 'movies'  => movies all day
    - 'shows'   => shows all day
    - 'mixed'   => shows by default; movies at 12–14 and 19–22
    """
    def day():
        hours = {}
        if kind == "movies":
            for h in range(24): hours[str(h)] = {"tags": "movies"}
        elif kind == "shows":
            for h in range(24): hours[str(h)] = {"tags": "shows"}
        else:
            for h in range(24): hours[str(h)] = {"tags": "shows"}
            for h in list(range(12, 15)) + list(range(19, 23)):
                hours[str(h)] = {"tags": "movies"}
        return hours
    return {
        "monday": day(), "tuesday": day(), "wednesday": day(),
        "thursday": day(), "friday": day(), "saturday": day(), "sunday": day(),
    }

def load_map(map_path: Path) -> dict:
    if map_path.exists():
        try:
            return json.loads(map_path.read_text())
        except Exception:
            pass
    return {}

def save_map(map_path: Path, m: dict):
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(m, indent=2))

def next_available(used: set[int], start=1, end=999) -> int:
    n = start
    while n <= end:
        if n not in used and n not in RESERVED:
            return n
        n += 1
    raise SystemExit("No free channel numbers available (avoiding 80–89).")

def build_conf(name: str, number: int, kind: str) -> dict:
    network_name = pretty_name(name)
    conf = {
      "station_conf": {
        "network_name": network_name,
        "channel_number": number,
        "network_type": "standard",
        "schedule_increment": 60,
        "break_strategy": "standard",
        "commercial_free": False,
        "break_duration": 120,
        "catalog_path": f"catalog/{name}_catalog.bin",
        "content_dir": f"catalog/{name}",
        "commercial_dir": "commercial",
        "bump_dir": "bump",
        "runtime_dir": f"runtime/{name}",
        "schedule_path": f"runtime/{name}_schedule.bin",
        "sign_off_video": "runtime/signoff.mp4",
        "off_air_video": "runtime/off_air_pattern.mp4",
        "standby_image": "runtime/standby.png",
        "normalize_title": True,
      }
    }
    conf["station_conf"].update(weekly_schedule(kind))
    return conf

def main():
    ap = argparse.ArgumentParser(description="Generate FS42 confs from catalog/")
    ap.add_argument("--fsroot", help="FieldStation42 root (default: /mnt/media01/projects/FieldStation42)")
    ap.add_argument("--list-only", action="store_true", help="Just list findings and assigned numbers")
    ap.add_argument("--prune", action="store_true", help="Delete confs for missing catalog folders")
    ap.add_argument("--reassign", action="store_true", help="Ignore saved map and reassign all numbers")
    ap.add_argument("--seed", type=int, help="Seed RNG before assigning numbers (optional)")
    args = ap.parse_args()

    fsroot = resolve_fsroot(args.fsroot)
    cat_root = fsroot / "catalog"
    conf_dir = fsroot / "confs"
    map_path = conf_dir / ".channel_map.json"

    if args.seed is not None:
        random.seed(args.seed)

    if not cat_root.is_dir():
        raise SystemExit(f"Missing catalog dir: {cat_root}")

    conf_dir.mkdir(parents=True, exist_ok=True)

    # discover channels from catalog/
    channels = []
    for entry in sorted(cat_root.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            kind = classify(entry)
            if kind != "empty":
                channels.append((entry.name, kind))

    # load or create mapping
    saved_map = {} if args.reassign else load_map(map_path)
    used = {v for v in saved_map.values() if isinstance(v, int)}
    plan = []
    for name, kind in channels:
        if isinstance(saved_map.get(name), int) and saved_map[name] not in RESERVED:
            num = saved_map[name]
        else:
            num = next_available(used, 1, 999)
            saved_map[name] = num
            used.add(num)
        plan.append((name, kind, num))

    if args.list_only:
        print(f"[fsroot] {fsroot}")
        print("Channels found:")
        for name, kind, num in plan:
            print(f"  - {name}  | kind={kind:6} | ch={num}")
        return

    # write conf files
    written = 0
    for name, kind, num in plan:
        conf = build_conf(name, num, kind if kind in ("movies","shows","mixed") else "shows")
        out = conf_dir / f"{name}.json"
        out.write_text(json.dumps(conf, indent=2))
        written += 1

    pruned = 0
    if args.prune:
        valid = {name for name, _, _ in plan}
        for f in conf_dir.glob("*.json"):
            if f.name == map_path.name:
                continue
            if f.stem not in valid:
                f.unlink(missing_ok=True)
                pruned += 1
        # drop dead entries from map too
        for k in list(saved_map.keys()):
            if k not in valid:
                saved_map.pop(k, None)

    save_map(map_path, saved_map)
    print(f"Confs written: {written}")
    if args.prune:
        print(f"Confs pruned:  {pruned}")
    print(f"Map saved:     {map_path}")

if __name__ == "__main__":
    main()
