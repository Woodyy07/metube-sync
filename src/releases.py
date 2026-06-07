import json

from ytmusicapi import YTMusic

from src.archive import load_artist


yt = YTMusic()


def get_new_releases(browse_id: str) -> list[dict]:
    """
    Fetch albums, EPs and singles for an artist, filtered against the archive.
    Returns list of {title, year, url, category} for new releases only.
    """
    archive = load_artist(browse_id)
    if archive is None:
        return []

    try:
        artist = yt.get_artist(browse_id)
    except Exception as e:
        raise RuntimeError(f"Could not fetch artist {browse_id}: {e}")

    releases = []

    for category in ("albums", "singles"):
        section = artist.get(category, {})
        section_id = section.get("browseId")
        params  = section.get("params")

        try:
            if params:
                results = yt.get_artist_albums(section_id, params, limit=None)
            else:
                results = [
                    yt.get_album(release["browseId"])
                    for release in section.get("results", [])
                ]
        except Exception as e:
            raise RuntimeError(f"Could not fetch {category} for {browse_id}: {e}")
        
        for album in results:
            playlist_id = album.get("playlistId") or album.get("audioPlaylistId")
            if not playlist_id:
                continue
                
            url = f"https://music.youtube.com/playlist?list={playlist_id}"
            if url in archive.releases:
                continue

            releases.append({
                "title":    album.get("title", "Unknown"),
                "year":     album.get("year", ""),
                "url":      url,
                "category": category,
            })

    return releases
