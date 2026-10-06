"""Shared paths and app.json I/O for the WaveStore scripts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_FILE = ROOT / "store.json"

RAW_BASE = "https://raw.githubusercontent.com/WaveLauncher/WaveStore/main"

# One root per kind and one folder per source, so the path says what a thing is
# and where it comes from. Nothing needs a flag inside the file to be sorted.
KINDS = {"app": "android_apps", "game": "android_games"}
KIND_FOLDERS = {folder: kind for kind, folder in KINDS.items()}
PROVIDERS = {"GitHub": "github", "HTML": "html", "PlayStore": "playstore"}
PROVIDER_SOURCES = {folder: source for source, folder in PROVIDERS.items()}

FIELD_ORDER = [
    "id", "name", "author", "description", "url", "source", "free",
    "categories", "screenSupport", "platformSupport", "icon", "screenshots",
    "playstore",
]

# Curated by hand, so no provider refresh may write them. "-modded" means the
# entry reaches that layout only with a patch or a mod.
SCREEN_SUPPORT = ["single", "dual", "single-modded", "dual-modded"]
PLATFORM_SUPPORT = ["android", "linux", "windows"]


def kind_folder(kind):
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"unknown kind {kind!r}, use one of {', '.join(sorted(KINDS))}")


def provider_folder(source):
    try:
        return PROVIDERS[source]
    except KeyError:
        raise ValueError(f"unknown source {source!r}, use one of {', '.join(sorted(PROVIDERS))}")


def icon_url(kind, source, app_id):
    return f"{RAW_BASE}/{kind_folder(kind)}/{provider_folder(source)}/{app_id}/icon.png"


def app_dir(kind, source, app_id):
    return ROOT / kind_folder(kind) / provider_folder(source) / app_id


def kind_of(directory):
    """The kind a folder stands for, or None when the path is not a kind root."""
    return KIND_FOLDERS.get(Path(directory).parent.parent.name)


def source_of(directory):
    """The source value a folder stands for, or None when it is not a provider."""
    return PROVIDER_SOURCES.get(Path(directory).parent.name)


def iter_app_dirs(kind=None):
    found = []
    for current in ([kind] if kind else sorted(KINDS)):
        for folder in sorted(PROVIDERS.values()):
            provider = ROOT / kind_folder(current) / folder
            if not provider.is_dir():
                continue
            found.extend(d for d in provider.iterdir() if d.is_dir() and not d.name.startswith("."))
    return sorted(found, key=lambda d: d.name)


def find_app_dir(app_id):
    """An id is unique across every kind and provider, so look everywhere."""
    for kind in sorted(KINDS):
        for folder in sorted(PROVIDERS.values()):
            candidate = ROOT / kind_folder(kind) / folder / app_id
            if (candidate / "app.json").exists():
                return candidate
    return None


def read_app(directory):
    return json.loads((Path(directory) / "app.json").read_text(encoding="utf-8"))


def order_fields(app):
    ordered = {k: app[k] for k in FIELD_ORDER if k in app}
    ordered.update({k: v for k, v in app.items() if k not in ordered})
    return ordered


def dump_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def write_app(directory, app):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "app.json").write_text(dump_json(order_fields(app)), encoding="utf-8")


def is_empty(value):
    """False is a real value, so truthiness cannot decide what is missing."""
    return value is None or value == "" or value == [] or value == {}


def merge_app(existing, incoming, fields, force=False):
    """Fill empty fields, keep local edits, and report what disagrees."""
    merged = dict(existing)
    changed, conflicts = [], []
    for key in fields:
        new = incoming.get(key)
        old = existing.get(key)
        if is_empty(new) or old == new:
            continue
        if is_empty(old) or force:
            merged[key] = new
            changed.append(key)
        else:
            conflicts.append((key, old, new))
    return merged, changed, conflicts
