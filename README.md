# metube-sync

Tracks new YouTube Music releases from followed artists and presents them for manual download.

## Pipeline

```
metube-sync → Download Management (MeTube) → Library Management (beets) → Streaming (Navidrome)
```

## Setup

```bash
uv sync
```

## Usage

```bash
# Follow an artist
uv run metube-sync add <artist>

# List followed artists
uv run metube-sync list

# Check one artist for new releases
uv run metube-sync check <artist>

# Check all followed artists
uv run metube-sync sync

# Unfollow an artist
uv run metube-sync remove <artist>
```

## Sync workflow

For each artist with new releases, `check` and `sync` display a table of new albums and singles, then prompt:

1. **Download** — select releases to get URLs for (all / 1 2 4 / none)
2. **Untrack** — select releases to skip forever (others / 1 2 4 / none)
3. Copy URLs into MeTube, confirm when done — releases are archived and won't appear again

## Data

```
data/
└── archive.json    # followed artists + their archived release URLs
```

Delete `data/archive.json` to reset everything.

## Credits

Built on top of [ytmusicapi](https://github.com/sigma67/ytmusicapi) by sigma67 and [MeTube](https://github.com/alexta69/metube) by alexta69.
