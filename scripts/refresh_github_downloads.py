import argparse
import json
import re
import sys
import urllib.error

import common

SOURCE = "GitHub"
PAGE_SIZE = 100
API = "https://api.github.com/repos/{owner}/{repo}/releases"
REPO_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class Skip(Exception):
    """This app cannot be counted. The message says why."""


class RateLimited(Exception):
    """Every later call fails the same way, so the run stops."""


def releases(owner, repo):
    page = 1
    while True:
        url = f"{API.format(owner=owner, repo=repo)}?per_page={PAGE_SIZE}&page={page}"
        try:
            with common.request(url, common.github_headers()) as response:
                batch = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 429):
                raise RateLimited("github rate limit or auth, set GITHUB_TOKEN") from exc
            if exc.code == 404:
                raise Skip("no such repository") from exc
            raise Skip(f"github api {exc.code}") from exc
        if not batch:
            return
        yield from batch
        # A short page is the last page, so stop without a request that returns nothing.
        if len(batch) < PAGE_SIZE:
            return
        page += 1


def total_downloads(owner, repo):
    """Return (downloads, release count, asset count)."""
    total = seen = assets = 0
    for release in releases(owner, repo):
        seen += 1
        for asset in release.get("assets") or []:
            count = asset.get("download_count")
            if isinstance(count, int):
                total += count
                assets += 1
    return total, seen, assets


def count_of(app):
    block = app.get("github")
    return block.get("downloadCount") if isinstance(block, dict) else None


def handle(app):
    """Return (new count, report line)."""
    match = REPO_RE.match((app.get("url") or "").strip())
    if not match:
        raise Skip(f"not a github repository: {app.get('url')!r}")
    total, seen, assets = total_downloads(match.group(1), match.group(2))
    if not seen:
        return total, "0  (no releases)"
    return total, f"{total:,}  ({seen} releases, {assets} assets)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_ids", nargs="*", help="app ids, or every GitHub app when empty")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    directories = [d for d in common.iter_app_dirs() if common.source_of(d) == SOURCE]
    if args.app_ids:
        wanted = set(args.app_ids)
        directories = [d for d in directories if d.name in wanted]
        for app_id in sorted(wanted - {d.name for d in directories}):
            print(f"{app_id:40} no GitHub app with that id")

    updated = unchanged = skipped = failed = 0
    for directory in directories:
        app = common.read_app(directory)
        try:
            total, report = handle(app)
        except RateLimited as exc:
            print(f"\nstopped: {exc}", file=sys.stderr)
            print(f"updated {updated}, unchanged {unchanged}, skipped {skipped}, failed {failed}")
            return 1
        except Skip as exc:
            print(f"{directory.name:40} SKIP {exc}", flush=True)
            skipped += 1
            continue
        except Exception as exc:  # one bad app must never stop the run
            print(f"{directory.name:40} FAIL {type(exc).__name__}: {exc}", flush=True)
            failed += 1
            continue

        if count_of(app) == total:
            unchanged += 1
            continue
        print(f"{directory.name:40} {report}", flush=True)
        updated += 1
        if not args.dry_run:
            app["github"] = {"downloadCount": total}
            common.write_app(directory, app)

    print(f"\nupdated {updated}, unchanged {unchanged}, skipped {skipped}, failed {failed}")
    if args.dry_run:
        print("dry run: nothing was written")
    if not common.github_headers().get("Authorization"):
        print("tip: set GITHUB_TOKEN to lift the 60 requests per hour api limit")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
