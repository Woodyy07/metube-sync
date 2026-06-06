import json
from dataclasses import dataclass, asdict

from src.config import ARTISTS


@dataclass
class Artist:
    name: str
    browse_id: str


def load() -> list[Artist]:
    if not ARTISTS.exists():
        return []
    content = ARTISTS.read_text().strip()
    if not content:
        return []
    return [Artist(**a) for a in json.loads(ARTISTS.read_text())]


def save(artists: list[Artist]) -> None:
    ARTISTS.parent.mkdir(parents=True, exist_ok=True)
    ARTISTS.write_text(json.dumps([asdict(a) for a in artists], indent=2))


def add(artist: Artist) -> bool:
    """Add artist to list. Returns False if already following."""
    artists = load()
    if any(a.browse_id == artist.browse_id for a in artists):
        return False
    artists.append(artist)
    save(artists)
    return True


def remove(browse_id: str) -> bool:
    """Remove artist by browse ID. Returns False if not found."""
    artists = load()
    filtered = [a for a in artists if a.browse_id != browse_id]
    if len(filtered) == len(artists):
        return False
    save(filtered)
    return True
