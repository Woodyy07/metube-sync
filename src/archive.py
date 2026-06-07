import json
from dataclasses import dataclass, asdict

from src.config import ARCHIVE


@dataclass
class Artist:
    name: str
    browse_id: str
    releases: list[str]


def _load() -> list[Artist]:
    if not ARCHIVE.exists():
        return []
    content = ARCHIVE.read_text().strip()
    if not content:
        return []

    return [Artist(**a) for a in json.loads(content)]


def _save(artists: list[Artist]) -> None:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps([asdict(a) for a in artists], indent=2))


def load_archive() -> list[Artist]:
    return _load()


def load_artist(browse_id: str) -> Artist | None:
    """Return the Artist matching the given browse ID."""
    return next((a for a in _load() if a.browse_id == browse_id), None)


def add_releases(browse_id: str, urls: list[str]) -> None:
    """Add new release URLs to an artist's archive, skipping duplicates."""
    artists = _load()

    artist = next((a for a in artists if a.browse_id == browse_id), None)
    if not artist:
        raise ValueError(f"Artist {browse_id!r} not found in archive")

    existing = set(artist.releases)
    artist.releases.extend(url for url in urls if url not in existing)

    _save(artists)


def add(artist: Artist) -> bool:
    """Add artist to list. Returns False if already following."""
    artists = _load()
    if any(a.browse_id == artist.browse_id for a in artists):
        return False
    
    artists.append(artist)
    _save(artists)
    return True


def remove(browse_id: str) -> bool:
    """Remove artist by browse ID. Returns False if not found."""
    artists = _load()
    filtered = [a for a in artists if a.browse_id != browse_id]
    if len(filtered) == len(artists):
        return False
    
    _save(filtered)
    return True
