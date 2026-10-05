# WaveStore

A curated catalog of Android emulators, tools and games, served as one JSON file.

```
https://raw.githubusercontent.com/WaveLauncher/WaveStore/main/store.json
```

51 apps and 37 games today. No API key, no account, no rate limit.

Wave Store was built for [Wave Launcher](https://github.com/WaveLauncher/WaveLauncher),
but it is not tied to it. **Anyone may use it for their app
store.** See [Using Wave Store](#using-wavestore) for the one condition.

---

## Using WaveStore

Fetch `store.json`, cache it, render it. The catalog is metadata only. It hosts
no APKs, so your client resolves downloads itself from the `url` and `source`
fields.

```json
{
  "version": 2,
  "generatedAt": "2026-10-05T12:57:45Z",
  "counts": { "apps": 51, "games": 37 },
  "featured": { "apps": [ ... ], "games": [ ... ] },
  "apps": [ ... ],
  "games": [ ... ]
}
```

`featured` holds 3 apps and 3 games for the current week. The entries are the
same objects that appear in `apps` and `games`, copied in full, so a front page
needs no lookup. At least one featured game is free.
Cronjob picks a new set every Monday.

Both lists hold the same object shape. An emulator is an app, something you play
is a game, and this repository decides which is which so your client does not
have to.

```json
{
  "id": "app.gamenative",
  "name": "GameNative",
  "author": "utkarshdalal",
  "description": "Native Windows game compatibility layer",
  "url": "https://github.com/utkarshdalal/GameNative",
  "source": "GitHub",
  "free": true,
  "categories": ["PC Emulation"],
  "icon": "https://raw.githubusercontent.com/WaveLauncher/WaveStore/main/android_apps/github/app.gamenative/icon.png"
}
```

| Field | Meaning |
|---|---|
| `id` | the Android package name, unique across both lists |
| `name` | display name |
| `author` | developer or organization |
| `description` | one line, absent when nobody wrote one |
| `url` | the repository, download page or Play listing |
| `source` | `GitHub`, `HTML` or `PlayStore` |
| `free` | false only for a paid Play Store entry |
| `categories` | at least one, the curated taxonomy |
| `icon` | an absolute URL, or `null` |
| `playstore` | Play-only extras, absent for every other source |

Two rules keep your client working as the catalog grows. Check `version` and
refuse one you do not know. Tell your JSON parser to ignore unknown fields.

### Caching

Download each icon once into a directory you own, record which URL it came
from, and read the file from then on. Fetch again only when the catalog gives
that `id` a different URL. The whole icon set is about 1 MB.

---

## Attribution

WaveStore is free to use, including commercially. One condition:

> **Credit Wave Store on the screen where the catalog appears, with a link to the Wave Store Repository.**

It must be on the store screen itself, where someone browsing your app can see it. A single line is enough:

```
Catalog by Wave Store (Wave Launcher)
github.com/WaveLauncher/WaveStore
```

Make the link tappable if your UI allows it. If your store screen genuinely has
no room, a credit on the first screen reachable from it is acceptable.

This is the attribution clause of CC BY 4.0, made specific so there is nothing to
guess about.

---

## License

This repository holds three different kinds of thing, and they are not covered by
one license.

| What | License |
|---|---|
| The scripts in `scripts/` | [MIT](LICENSE) |
| The catalog: `android_apps/`, `android_games/`, `store.json` | [CC BY 4.0](LICENSE-DATA) |
| App icons, names and descriptions | **not ours to license**, see below |

### Third-party content

The icons come out of each app's own APK or its Play Store listing. The names and
descriptions come from the developers. **WaveStore does not own any of it and
grants you no rights to it.** Those remain the property of their developers and
publishers.

What CC BY 4.0 covers here is the catalog itself: which apps are in it, how they
are categorized, the structure of the data, and the work of assembling it.

Using an app's icon and name to list that app is ordinary nominative use, the
same thing every app store does. That is almost certainly fine for a store
listing and is not something WaveStore can grant or withhold. If a developer asks
to be removed, open an issue and they will be removed.

---

## Repository layout

```
android_apps/
  github/     44   a GitHub repository, resolve the latest release
  html/        7   a project download page
  playstore/   0   a Play Store listing
android_games/
  playstore/  37
store.json         the generated catalog
scripts/           the public tools
```

The path carries the meaning, and the build rejects a folder that breaks it:

1. The root is the kind, `android_apps` or `android_games`.
2. The provider folder matches the `source` field.
3. The folder name is the package name and equals the `id` field. It is unique
   across every kind and provider.

A `playstore` entry keeps its icon on the Play CDN, so it has no `icon.png`.

---

## Tools

Python 3.9 or newer. Only the Play Store script has a dependency.

```
pip install -r requirements.txt
```

### Build the catalog

```
python3 scripts/build_store.py
```

Reads every `app.json`, checks it, and writes `store.json`. Exits 1 and writes
nothing when an entry is broken. Lists the apps that have no icon.

### Add Play Store apps

```
python3 scripts/add_playstore.py <ids or urls> [--categories Racing] [--type app|game] [--dry-run] [--force]
```

Takes package ids, Play Store urls, or a comma separated list of both. Reads the
listing and writes the metadata and the Play CDN icon link. It downloads no
image.

A new entry lands in `android_games/` when the Play genre starts with `GAME_`,
and in `android_apps/` otherwise. Play files emulators under `GAME_*` too, so
pass `--type app` for those. It fills empty fields and never overwrites a hand
edit without `--force`.

There is also a `.github/workflows/add-playstore.yml` that does the same from the
Actions tab.

### Refresh the featured list

```
python3 scripts/pick_featured.py [--dry-run]
```

Picks 3 apps and 3 games at random and writes them into the `featured` block of
`store.json`. Run `build_store.py` first, so the picker draws from a current
catalog.

Games come from the Play Store only, and at least one of the three is free. Apps
come from `GitHub` or `PlayStore`. A new set never repeats an id that is
featured now. A later rebuild keeps the selection and refreshes each entry from
its `app.json`.

### Adding an app by hand

Write `android_apps/<provider>/<id>/app.json`, drop an `icon.png` beside it, and
run the build. A pull request is welcome.

---

## Continuous integration

`.github/workflows/build-store.yml` rebuilds `store.json` on a push to `main` and
fails a pull request when the catalog is stale or an entry is broken.

`.github/workflows/refresh-featured.yml` picks a new featured list every Monday
at 12:00 UTC, rebuilds the catalog, and commits both files. Start it by hand from
the Actions tab to change the week early.
