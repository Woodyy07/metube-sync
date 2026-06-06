import json

from ytmusicapi import YTMusic

from src.config import ARCHIVE


yt = YTMusic()


def _load_archive() -> list[str]:
    if not ARCHIVE.exists():
        return []
    return json.loads(ARCHIVE.read_text())


def get_new_releases(browse_id: str) -> list[dict]:
    """
    Fetch albums, EPs and singles for an artist, filtered against the archive.
    Returns list of {title, year, url, category} for new releases only.
    """
    archive = _load_archive()

    try:
        artist = yt.get_artist(browse_id)
    except Exception as e:
        raise RuntimeError(f"Could not fetch artist {browse_id}: {e}")

    releases = []

    for category in ("albums", "singles"):
        section = artist.get(category, {})
        id = section.get("browseId")
        params  = section.get("params")
        if params:
            try:
                results = yt.get_artist_albums(id, params, limit=None)
            except Exception as e:
                results = section.get("results", [])
        else:
            results = section.get("results", [])

        for release in results:
            release_id = release.get("browseId")
            if not release_id:
                continue

            try:
                album = yt.get_album(release_id)
                playlist_id = album.get("audioPlaylistId")
                if not playlist_id:
                    continue
                
                url = f"https://music.youtube.com/playlist?list={playlist_id}"
            except Exception:
                continue

            if url in archive:
                continue

            releases.append({
                "title":    release.get("title", "Unknown"),
                "year":     release.get("year", ""),
                "url":      url,
                "category": category,
            })

    return releases


def archive_releases(urls: list[str]) -> None:
    """Mark URLs as archived (downloaded/untracked) so they're skipped on future syncs."""
    archive = _load_archive()
    archive.extend(u for u in urls if u not in archive)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps(archive, indent=2))
