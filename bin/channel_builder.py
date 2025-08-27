#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import shutil

APP_ROOT = os.environ.get("FS42_PROJECT_ROOT", "/mnt/media01/projects/FieldStation42")
CATALOG_DIR = os.path.join(APP_ROOT, "catalog")
CONFS_DIR = os.path.join(APP_ROOT, "confs")
RUNTIME_DIR = os.path.join(APP_ROOT, "runtime")
HLS_DIR = os.path.join(APP_ROOT, "page_stream", "hls")
WEB_URLS_DIR = os.path.join(APP_ROOT, "page_stream", "web_urls")

CONTENT_TAGS = ["cartoon", "shows", "movie", "late"]
EVENT_TAGS = ["signoff", "off_air"]
ALL_TAGS = CONTENT_TAGS + EVENT_TAGS


def safe_name(name):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)


def list_channels():
    print("\n📺 Existing Channels:")
    files = [f for f in os.listdir(CONFS_DIR) if f.endswith(".json") and not f.startswith("web_")]
    if not files:
        print("⚠️ No channels found.")
        return []
    for i, name in enumerate(files):
        print(f"[{i}] {name[:-5]}")
    return files


def delete_channel():
    channels = list_channels()
    if not channels:
        return
    choice = input("Enter number to delete (or Q to cancel): ").strip().lower()
    if choice == "q":
        return
    if not choice.isdigit() or int(choice) >= len(channels):
        print("❌ Invalid choice.")
        return
    name = channels[int(choice)].replace(".json", "")
    print(f"🗑 Deleting channel '{name}'...")
    os.remove(os.path.join(CONFS_DIR, f"{name}.json"))
    shutil.rmtree(os.path.join(CATALOG_DIR, name), ignore_errors=True)
    shutil.rmtree(os.path.join(RUNTIME_DIR, name), ignore_errors=True)
    shutil.rmtree(os.path.join(HLS_DIR, name), ignore_errors=True)
    web_url = os.path.join(WEB_URLS_DIR, f"{name}.json")
    if os.path.exists(web_url):
        os.remove(web_url)
    print("✅ Channel deleted.")


def browse_for_file(title, start_dir, exts=None, folder=False):
    exts = exts or []
    current = os.path.abspath(os.path.expanduser(start_dir))
    root = current

    while True:
        print(f"\n📂 {title} – Browsing: {current}")
        try:
            items = os.listdir(current)
        except PermissionError:
            print("❌ Permission denied.")
            current = os.path.dirname(current)
            continue

        entries = []
        if os.path.abspath(current) != os.path.abspath(root):
            entries.append(("..", os.path.abspath(os.path.join(current, ".."))))

        for name in sorted(items):
            full = os.path.join(current, name)
            if os.path.isdir(full):
                entries.append((f"{name}/", full))
            elif os.path.isfile(full) and not folder:
                if not exts or any(name.lower().endswith(ext) for ext in exts):
                    entries.append((name, full))

        for i, (label, _) in enumerate(entries):
            print(f"[{i}] {label}")
        print("[Enter] or '.' to select this folder" if folder else "")
        print("[R] Reset  [Q] Cancel")

        choice = input("Pick a number: ").strip().lower()
        if choice == 'q':
            return None
        elif choice == 'r':
            current = root
            continue
        elif choice == '' or choice == '.':
            if folder:
                return current
            print("❌ Must select a file.")
            continue
        elif not choice.isdigit() or int(choice) >= len(entries):
            print("❌ Invalid choice. Try again.")
            continue

        selected = entries[int(choice)][1]
        if os.path.isdir(selected):
            current = selected
        else:
            return selected


def confirm_selection(path):
    print(f"✅ Selected: {path}")
    while True:
        choice = input("[C] Continue  [R] Redo  [Q] Quit: ").strip().lower()
        if choice in ['c', 'r', 'q']:
            return choice


def link_folder_to_tag(tag, target_folder):
    while True:
        source = browse_for_file(f"Select folder for tag '{tag}'", "/mnt/media01/downloads/completed", folder=True)
        if not source or not os.path.isdir(source):
            print(f"⚠️ Skipped linking for tag: {tag}")
            return
        print(f"✅ Linked folder: {source}")
        if confirm_selection(source) == 'r':
            continue
        os.makedirs(target_folder, exist_ok=True)
        for entry in os.listdir(source):
            src = os.path.join(source, entry)
            dst = os.path.join(target_folder, entry)
            if not os.path.exists(dst):
                os.symlink(src, dst)
        break


def build_schedule():
    print("\n📆 Build 7-day schedule:")
    print("Available Tags:")
    for i, tag in enumerate(ALL_TAGS):
        print(f"[{i}] {tag}")
    print("[Enter]=repeat | r=undo | q=quit\n")

    schedule = {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for d, day in enumerate(days):
        print(f"\n📅 {day.title()}:")
        if d > 0 and input("Copy previous day? (Y/n): ").strip().lower() in ['', 'y']:
            schedule[day] = schedule[days[d - 1]].copy()
            continue

        hour = 0
        last_tag = None
        day_sched = {}
        while hour < 24:
            raw = input(f"Hour {hour:02d}: ").strip().lower()
            if raw == "q": exit()
            elif raw == "r" and hour > 0:
                hour -= 1
                del day_sched[str(hour)]
                continue
            elif raw == "" and last_tag:
                tag = last_tag
            elif raw.isdigit() and int(raw) < len(ALL_TAGS):
                tag = ALL_TAGS[int(raw)]
            else:
                print("❌ Invalid input.")
                continue

            if tag in EVENT_TAGS:
                day_sched[str(hour)] = {"event": tag}
            else:
                day_sched[str(hour)] = {"tags": tag}
            last_tag = tag
            hour += 1
        schedule[day] = day_sched
    return schedule


def build_channel():
    print("\n🎬 Create New Channel\n")
    name = safe_name(input("Channel name: "))
    number = int(input("Channel number: "))

    content_dir = os.path.join(CATALOG_DIR, name)
    runtime_dir = os.path.join(RUNTIME_DIR, name)
    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(runtime_dir, exist_ok=True)

    conf = {
        "station_conf": {
            "network_name": name,
            "channel_number": number,
            "network_type": "standard",
            "schedule_increment": 60,
            "break_strategy": "standard",
            "commercial_free": False,
            "break_duration": 120,
            "catalog_path": f"catalog/{name}_catalog.bin",
            "content_dir": content_dir,
            "commercial_dir": browse_for_file("Commercial Folder", "/mnt", folder=True),
            "bump_dir": browse_for_file("Bump Folder", "/mnt", folder=True),
            "runtime_dir": runtime_dir,
            "schedule_path": f"{runtime_dir}_schedule.bin",
            "sign_off_video": browse_for_file("Sign-Off (MP4)", "/mnt", [".mp4"]),
            "off_air_video": browse_for_file("Off-Air (MP4)", "/mnt", [".mp4"]),
            "standby_image": browse_for_file("Standby Image (PNG)", "/mnt", [".png"]),
            "be_right_back_media": browse_for_file("Be Right Back Media (MP4/PNG)", "/mnt", [".mp4", ".png"]),
            "normalize_title": True
        }
    }

    for tag in CONTENT_TAGS:
        link_folder_to_tag(tag, os.path.join(content_dir, tag))

    schedule = build_schedule()
    conf["station_conf"].update(schedule)

    if input("Include clip_shows? (Y/n): ").strip().lower() != 'n':
        conf["clip_shows"] = [
            { "tags": "cartoon", "duration": 30 },
            { "tags": "shows", "duration": 30 },
            { "tags": "movie", "duration": 120 },
            { "tags": "late", "duration": 30 }
        ]

    out_path = os.path.join(CONFS_DIR, f"{name}.json")
    with open(out_path, "w") as f:
        json.dump(conf, f, indent=2)
    print(f"\n✅ Saved: {out_path}")
    return name


def rebuild_catalog(channel_name):
    print(f"\n⚙️ Rebuilding {channel_name}...")
    subprocess.run([
        "python3",
        os.path.join(APP_ROOT, "station_42.py"),
        "--rebuild_catalog", "--add_day", "all", "--force", "--schedule", "--verbose"
    ], check=True)


def main():
    while True:
        print("\n📺 FieldStation42 Channel Menu")
        print("[1] Create new channel")
        print("[2] List channels")
        print("[3] Delete a channel")
        print("[Q] Quit")
        cmd = input("> ").strip().lower()
        if cmd == "1":
            ch = build_channel()
            if input("Rebuild catalog now? (Y/n): ").lower() != 'n':
                rebuild_catalog(ch)
        elif cmd == "2":
            list_channels()
        elif cmd == "3":
            delete_channel()
        elif cmd == "q":
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
