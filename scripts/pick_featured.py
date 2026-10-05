"""Pick the weekly featured apps and games into store.json.

Writes the whole entry, not the id, so a client reads the front page out of the
featured block alone. build_store.py keeps the selection across a rebuild.
"""

import argparse
import json
import random
import sys

import common

COUNT = 3
APP_SOURCES = {"GitHub", "PlayStore"}
GAME_SOURCES = {"PlayStore"}
KEY_ORDER = ["version", "generatedAt", "counts", "featured", "apps", "games"]


def current_ids(store):
    """What is featured now, so the next selection can avoid it."""
    picked = store.get("featured") or {}
    return {entry["id"] for key in ("apps", "games") for entry in picked.get(key) or []}


def fresh(pool, exclude):
    """A catalog too small to rotate still has to produce a list."""
    remaining = [a for a in pool if a["id"] not in exclude]
    return remaining if len(remaining) >= COUNT else pool


def pick_games(pool, exclude):
    candidates = fresh(pool, exclude)
    free = [g for g in candidates if g.get("free")] or [g for g in pool if g.get("free")]
    if not free:
        raise ValueError("no free game in the catalog, cannot satisfy the free rule")
    first = random.choice(free)
    chosen = [first] + random.sample([g for g in candidates if g["id"] != first["id"]], COUNT - 1)
    random.shuffle(chosen)
    return chosen


def main():
    parser = argparse.ArgumentParser(description="Pick the weekly featured apps and games.")
    parser.add_argument("--dry-run", action="store_true", help="print the selection and write nothing")
    args = parser.parse_args()

    if not common.STORE_FILE.exists():
        print("error: store.json is missing, run build_store.py first", file=sys.stderr)
        return 1
    store = json.loads(common.STORE_FILE.read_text(encoding="utf-8"))

    apps = [a for a in store.get("apps") or [] if a.get("source") in APP_SOURCES]
    games = [g for g in store.get("games") or [] if g.get("source") in GAME_SOURCES]
    for label, pool in (("app", apps), ("game", games)):
        if len(pool) < COUNT:
            print(f"error: only {len(pool)} {label}(s) are eligible, need {COUNT}", file=sys.stderr)
            return 1

    exclude = current_ids(store)
    try:
        chosen_games = pick_games(games, exclude)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    chosen_apps = random.sample(fresh(apps, exclude), COUNT)

    for entry in chosen_apps:
        print(f"app   {entry['id']}  {entry['name']}")
    for entry in chosen_games:
        print(f"game  {entry['id']}  {entry['name']}  {'free' if entry.get('free') else 'paid'}")

    if args.dry_run:
        print("\ndry run: store.json was not written")
        return 0

    store["featured"] = {"apps": chosen_apps, "games": chosen_games}
    ordered = {k: store[k] for k in KEY_ORDER if k in store}
    ordered.update({k: v for k, v in store.items() if k not in ordered})
    common.STORE_FILE.write_text(common.dump_json(ordered), encoding="utf-8")
    print("\nwrote the featured block into store.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
