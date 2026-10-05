"""Add Google Play apps to android_apps/<id>/app.json.

Needs google-play-scraper:  pip install -r requirements.txt

The icon stays on the Play CDN. Nothing is downloaded into the repo.
"""

import argparse
import html
import re
import sys

import common

SOURCE = "PlayStore"
STORE_URL = "https://play.google.com/store/apps/details?id={app_id}"
ICON_SIZE = "s512"
PLAY_CDN = "play-lh.googleusercontent.com"
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
URL_ID_RE = re.compile(r"[?&]id=([A-Za-z0-9_.]+)")
GENERATED_FIELDS = ["name", "author", "description", "url", "source", "categories", "icon"]
# Play owns these, so they refresh instead of raising a conflict.
PLAY_OWNED = ["free", "playstore"]


def parse_targets(values):
    """Accept package ids, Play Store urls, and comma separated lists of both."""
    found = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            match = URL_ID_RE.search(part)
            app_id = match.group(1) if match else part
            if app_id not in found:
                found.append(app_id)
    return found


def play_icon(url):
    base = url.split("=")[0]
    return f"{base}={ICON_SIZE}" if PLAY_CDN in base else url


def play_kind(record):
    """Play files anything playable under GAME_*, emulators included."""
    return "game" if (record.get("genreId") or "").startswith("GAME_") else "app"


def play_extras(record):
    """The Play-only facts. Everything a client needs sits at the root."""
    # An entry with no id is a descriptive tag, such as "Single player".
    names = [
        (entry.get("name") or "").strip()
        for entry in (record.get("categories") or [])
        if entry.get("id") and (entry.get("name") or "").strip()
    ]
    genre = (record.get("genre") or "").strip()
    if genre and genre not in names:
        names.insert(0, genre)
    score = record.get("score")
    return {
        "categories": names,
        "score": round(score, 2) if isinstance(score, (int, float)) else None,
        "downloadCount": record.get("realInstalls"),
    }


def convert(record, app_id, categories):
    summary = html.unescape(record.get("summary") or "")
    return {
        "id": app_id,
        "name": (record.get("title") or app_id).strip(),
        "author": (record.get("developer") or "").strip(),
        "description": " ".join(summary.split()),
        "url": STORE_URL.format(app_id=app_id),
        "source": SOURCE,
        "free": bool(record.get("free")),
        "categories": categories or [(record.get("genre") or "Other").strip()],
        "icon": play_icon(record.get("icon") or ""),
        "playstore": play_extras(record),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="package ids or Play Store urls, comma separated")
    parser.add_argument("--categories", default="", help="store categories for every app in this run")
    parser.add_argument(
        "--type",
        choices=sorted(common.KINDS),
        default="",
        help="force app or game instead of reading the Play genre",
    )
    parser.add_argument("--lang", default="en")
    parser.add_argument("--country", default="us")
    parser.add_argument("--force", action="store_true", help="overwrite local edits")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    try:
        from google_play_scraper import app as fetch_app
        from google_play_scraper.exceptions import NotFoundError
    except ImportError:
        print("google-play-scraper is missing. Run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    created, updated, unchanged, conflicts, failed, guessed, misfiled = [], [], [], [], [], [], []

    for app_id in parse_targets(args.targets):
        if not PACKAGE_RE.match(app_id):
            failed.append((app_id, "not an Android package name"))
            continue
        try:
            record = fetch_app(app_id, lang=args.lang, country=args.country)
        except NotFoundError:
            failed.append((app_id, "not on the Play Store"))
            continue
        except Exception as exc:
            failed.append((app_id, f"{type(exc).__name__}: {exc}"))
            continue

        app = convert(record, app_id, categories)
        if not categories:
            guessed.append((app_id, app["categories"][0]))
        kind = args.type or play_kind(record)
        directory = common.find_app_dir(app_id)
        if directory is None:
            directory = common.app_dir(kind, SOURCE, app_id)
        elif common.kind_of(directory) != kind:
            misfiled.append((app_id, common.kind_of(directory), kind))

        if (directory / "app.json").exists():
            existing = common.read_app(directory)
            merged, changed, app_conflicts = common.merge_app(
                existing, app, GENERATED_FIELDS, args.force
            )
            # An app tracked under another source keeps its own values.
            if merged.get("source") == SOURCE:
                for key in PLAY_OWNED:
                    if existing.get(key) != app[key]:
                        merged[key] = app[key]
                        changed.append(key)
            for key, old, new in app_conflicts:
                conflicts.append((app_id, key, old, new))
            if changed:
                updated.append((app_id, changed))
                if not args.dry_run:
                    common.write_app(directory, merged)
            elif not app_conflicts:
                unchanged.append(app_id)
        else:
            created.append((app_id, app["name"]))
            if not args.dry_run:
                common.write_app(directory, app)

    for app_id, name in created:
        print(f"create   {app_id}  {name}")
    for app_id, changed in updated:
        print(f"update   {app_id}  {', '.join(changed)}")
    for app_id in unchanged:
        print(f"ok       {app_id}")
    for app_id, key, old, new in conflicts:
        print(f"conflict {app_id}  {key}: kept {old!r}, Play has {new!r}")
    for app_id, current, wanted in misfiled:
        print(f"kind     {app_id}  sits in {current}s, Play says {wanted}. Move the folder to change it.")
    for app_id, category in guessed:
        print(f"category {app_id}  guessed {category!r} from the Play genre, pass --categories to set it")
    for app_id, reason in failed:
        print(f"FAIL     {app_id}  {reason}")

    print(
        f"\ncreated {len(created)}, updated {len(updated)}, unchanged {len(unchanged)}, "
        f"conflicts {len(conflicts)}, failed {len(failed)}"
    )
    if conflicts:
        print("re-run with --force to take the Play values")
    if args.dry_run:
        print("dry run: nothing was written")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
