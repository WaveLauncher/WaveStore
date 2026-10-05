"""Join every app.json under the kind roots into store.json."""

import json
import sys
from datetime import datetime, timezone

import common

STORE_VERSION = 2
REQUIRED = ["id", "name", "url", "source", "categories"]


def collect():
    entries = {kind: [] for kind in common.KINDS}
    errors, no_icon = [], []
    seen = {}

    for directory in common.iter_app_dirs():
        path = directory / "app.json"
        if not path.exists():
            errors.append(f"{directory}: no app.json")
            continue
        try:
            app = common.read_app(directory)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid json: {exc}")
            continue

        missing = [f for f in REQUIRED if not app.get(f)]
        if missing:
            errors.append(f"{path}: missing {', '.join(missing)}")
            continue
        # A plain truthiness check would read free: false as missing.
        if not isinstance(app.get("free"), bool):
            errors.append(f"{path}: free must be true or false")
            continue
        if app["id"] != directory.name:
            errors.append(f"{path}: id {app['id']!r} does not match the folder name")
            continue

        kind = common.kind_of(directory)
        folder_source = common.source_of(directory)
        if kind is None or folder_source is None:
            errors.append(f"{path}: not inside a <kind>/<provider>/ folder")
            continue
        if app["source"] != folder_source:
            errors.append(
                f"{path}: source {app['source']!r} does not match the {directory.parent.name}/ folder"
            )
            continue
        if app["id"] in seen:
            errors.append(f"{path}: duplicate id, already defined in {seen[app['id']]}")
            continue
        seen[app["id"]] = path

        stored = (app.get("icon") or "").strip()
        if (directory / "icon.png").exists():
            app["icon"] = common.icon_url(kind, app["source"], app["id"])
        elif stored.startswith("http") and not stored.startswith(common.RAW_BASE):
            # A provider hosts this icon itself, such as the Play Store cdn.
            app["icon"] = stored
        else:
            app["icon"] = None
            no_icon.append(app["id"])

        entries[kind].append(common.order_fields(app))

    for kind in entries:
        entries[kind].sort(key=lambda a: a["id"])
    return entries, errors, no_icon


def featured(entries, previous):
    """Carry the selection across a rebuild.

    store.json holds the picked entries in full, so a rebuild from scratch would
    drop them. Keep the ids and resolve them again, which also makes a featured
    entry follow an edit to its app.json.
    """
    chosen = {kind: [] for kind in common.KINDS}
    picked = previous.get("featured") or {}
    for kind in chosen:
        by_id = {app["id"]: app for app in entries[kind]}
        for entry in picked.get(f"{kind}s") or []:
            app_id = entry.get("id") if isinstance(entry, dict) else entry
            if app_id in by_id:
                chosen[kind].append(by_id[app_id])
            else:
                print(f"warning: featured {kind} {app_id!r} is not in the catalog", file=sys.stderr)
    return {f"{kind}s": chosen[kind] for kind in sorted(chosen)}


def main():
    entries, errors, no_icon = collect()

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} problem(s), store.json not written", file=sys.stderr)
        return 1

    apps, games = entries["app"], entries["game"]
    previous = {}
    if common.STORE_FILE.exists():
        try:
            previous = json.loads(common.STORE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}

    picked = featured(entries, previous)
    unchanged = (
        previous.get("version") == STORE_VERSION
        and previous.get("apps") == apps
        and previous.get("games") == games
        and previous.get("featured") == picked
    )
    if unchanged:
        print(f"store.json already current ({len(apps)} apps, {len(games)} games)")
        return 0

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    store = {
        "version": STORE_VERSION,
        "generatedAt": generated_at,
        "counts": {"apps": len(apps), "games": len(games)},
        "featured": picked,
        "apps": apps,
        "games": games,
    }
    common.STORE_FILE.write_text(common.dump_json(store), encoding="utf-8")

    print(f"wrote store.json ({len(apps)} apps, {len(games)} games)")
    if no_icon:
        print(f"no icon.png ({len(no_icon)}):")
        for app_id in no_icon:
            print(f"  {app_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
