#!/usr/bin/env python3
import os, json, random

base_dir = os.path.dirname(os.path.abspath(__file__))
fs42_custom = os.path.abspath(os.path.join(base_dir, ".."))

# Directory setup
conf_dir = os.path.join(fs42_custom, "confs")
catalog_dir = os.path.join(fs42_custom, "catalog")
runtime_dir = os.path.join(fs42_custom, "runtime")

for d in (conf_dir, catalog_dir, runtime_dir):
    os.makedirs(d, exist_ok=True)

# List of your 40 channels with types
channels = [
    # Streaming (with real test streams)
    ("Streamy", "streaming", "http://sample.vodobox.net/skate_phantom_flex_4k/skate_phantom_flex_4k.m3u8"),
    ("NatureStream", "streaming", "https://ireplay.tv/test/blender.m3u8"),
    ("NewsNow", "streaming", "http://walterebert.com/playground/video/hls/sintel-trailer.m3u8"),
    ("SportsStream", "streaming", "https://devimages.apple.com.edgekey.net/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8"),
    ("WeatherCam", "streaming", "http://devimages.apple.com.edgekey.net/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8"),

    # Loop channels
    ("Junk", "loop", None),
    ("MusicBox", "loop", None),
    ("ShortsTV", "loop", None),
    ("CartoonLoops", "loop", None),
    ("AnimeLoops", "loop", None),

    # Traditional channels
    ("TrashTV", "traditional", None),
    ("CartoonRiver", "traditional", None),
    ("Sun", "traditional", None),
    ("True", "traditional", None),
    ("Mouse", "traditional", None),
    ("Indie42", "traditional", None),
    ("RetroAnimeTV", "traditional", None),
    ("NewAnimeTV", "traditional", None),
    ("MonsterVision", "traditional", None),
    ("HeavyMetal", "traditional", None),
    ("WildToon", "traditional", None),
    ("CrimeTime", "traditional", None),
    ("ActionMax", "traditional", None),
    ("ComedyHub", "traditional", None),
    ("DramaWorks", "traditional", None),
    ("SciFiWorld", "traditional", None),
    ("RomanceTV", "traditional", None),
    ("ClassicsTV", "traditional", None),
    ("PublicBroadcasting", "traditional", None),
    ("80sTV", "traditional", None),
    ("90sTV", "traditional", None),

    # Movie-only networks (traditional style with no schedule of "shows")
    ("RetroAnimeMovies", "traditional", None),
    ("AnimationVault", "traditional", None),
    ("MonsterMovies", "traditional", None),
    ("ClassicMovies", "traditional", None),
    ("IndieMovies", "traditional", None),
    ("SciFiMovies", "traditional", None),
    ("ActionMovies", "traditional", None),
    ("ComedyMovies", "traditional", None),
    ("RomanceMovies", "traditional", None),
]

# Function to build 24-slot randomized schedules
def make_schedule():
    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    schedule = {d: {str(h): random.choice(["shows","movies"]) for h in range(24)} for d in days}
    return schedule

# Generate configs and folders
for idx, (name, ctype, stream_url) in enumerate(channels, start=1):
    conf = {"station_conf": {
        "network_name": name,
        "network_type": ctype,
        "channel_number": idx,
        "network_long_name": f"My {name} Channel"
    }}
    slug = name.lower()

    if ctype == "streaming":
        conf["station_conf"]["runtime_dir"] = f"runtime/{slug}"
        os.makedirs(os.path.join(runtime_dir, slug), exist_ok=True)
        conf["station_conf"]["streams"] = [{"url": stream_url, "duration": 30, "title": name}] if stream_url else []

    elif ctype == "loop":
        conf["station_conf"]["content_dir"] = f"catalog/{slug}"
        os.makedirs(os.path.join(catalog_dir, slug, "videos"), exist_ok=True)

    else:  # traditional
        conf["station_conf"]["content_dir"] = f"catalog/{slug}"
        os.makedirs(os.path.join(catalog_dir, slug, "shows"), exist_ok=True)
        os.makedirs(os.path.join(catalog_dir, slug, "movies"), exist_ok=True)
        conf["station_conf"].update(make_schedule())

    with open(os.path.join(conf_dir, f"{slug}.json"), "w") as f:
        json.dump(conf, f, indent=4)

print(f"✅ Generated {len(channels)} channel configs and folders")
