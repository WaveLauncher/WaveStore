# WaveStore

A curated JSON catalog of Android emulators, tools, and games.

```text
https://raw.githubusercontent.com/WaveLauncher/WaveStore/main/store.json
```

Built for [Wave Launcher](https://github.com/WaveLauncher/WaveLauncher), but available for other app stores under the attribution requirement below.

## Use the Catalog

Fetch and cache `store.json`. The catalog contains metadata only; clients must resolve downloads from each entry's `url` and `source`.

```json
{
  "version": 2,
  "generatedAt": "2026-10-05T12:57:45Z",
  "counts": { "apps": 52, "games": 134 },
  "featured": { "apps": [], "games": [] },
  "apps": [],
  "games": []
}
```

`featured` contains three apps and three games. Entries are complete copies of items in `apps` and `games`.

Both lists use the same entry shape:

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
  "screenSupport": ["single"],
  "platformSupport": ["android"],
  "icon": "https://raw.githubusercontent.com/WaveLauncher/WaveStore/main/android_apps/github/app.gamenative/icon.png"
}
```

| Field | Meaning |
|---|---|
| `id` | Android package name; unique across all entries |
| `name` | Display name |
| `author` | Developer or organization |
| `description` | Optional one-line description |
| `url` | Repository, download page, or Play Store listing |
| `source` | `GitHub`, `HTML`, or `PlayStore` |
| `free` | `false` only for paid Play Store entries |
| `categories` | Curated categories |
| `screenSupport` | `single`, `dual`, `single-modded`, or `dual-modded` |
| `platformSupport` | `android`, `linux`, and/or `windows` |
| `icon` | Absolute icon URL or `null` |
| `github` | GitHub-specific fields; absent for other sources |
| `playstore` | Play Store-specific fields; absent for other sources |

A `-modded` `screenSupport` value means dual-screen support requires a patch or mod.

Check `version` before using a catalog, and configure JSON parsing to ignore unknown fields. Cache icons locally and re-download one only when its URL changes.

## Attribution

WaveStore is free for commercial and non-commercial use under CC BY 4.0. Credit Wave Store on the screen where the catalog appears, with a link to this repository.

```text
Catalog by Wave Store (Wave Launcher)
github.com/WaveLauncher/WaveStore
```

Make the link tappable where possible. If the store screen has no room, place the credit on the first screen reachable from it.

## Development

### Prerequisites

- Python 3.9 or later

### Install

```sh
pip install -r requirements.txt
```

Only the Play Store import script requires dependencies.

### Build and Validate

```sh
python3 scripts/build_store.py
```

The command validates every `app.json` and writes `store.json`. It exits with status 1 without writing output when an entry is invalid.

### Add Play Store Entries

```sh
python3 scripts/add_playstore.py <ids-or-urls> [--categories Racing] [--type app|game] [--dry-run] [--force]
```

Accepts package IDs, Play Store URLs, or a comma-separated combination. Emulator listings categorized by Play Store as games require `--type app`.

### Refresh Featured Entries

```sh
python3 scripts/pick_featured.py [--dry-run]
```

Run `build_store.py` first. This selects three apps and three games, including at least one free game.

### Add an Entry Manually

Create:

```text
android_apps/<provider>/<id>/app.json
```

Add `icon.png` beside it when applicable, then run:

```sh
python3 scripts/build_store.py
```

## License

| Content | License |
|---|---|
| Scripts in `scripts/` | [MIT](LICENSE) |
| Catalog data in `android_apps/`, `android_games/`, and `store.json` | [CC BY 4.0](LICENSE-DATA) |
| App icons, names, and descriptions | Owned by their respective developers and publishers |

WaveStore does not grant rights to third-party icons, names, or descriptions.
