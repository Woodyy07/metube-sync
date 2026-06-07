import json
import pytest
from src.archive import Artist


# ── Archive fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def tmp_archive(tmp_path, monkeypatch):
    """Patch ARCHIVE to a temp file. Returns the path."""
    archive_file = tmp_path / "archive.json"
    monkeypatch.setattr("src.archive.ARCHIVE", archive_file)
    return archive_file


@pytest.fixture
def artist():
    return Artist(name="Lekkerfaces", browse_id="UC123", releases=[])


@pytest.fixture
def artist_with_releases():
    return Artist(
        name="Lekkerfaces",
        browse_id="UC123",
        releases=["https://music.youtube.com/playlist?list=OLAK_existing"],
    )


@pytest.fixture
def populated_archive(tmp_archive, artist):
    """Temp archive with one artist, no releases."""
    tmp_archive.write_text(json.dumps([
        {"name": artist.name, "browse_id": artist.browse_id, "releases": []}
    ]))
    return tmp_archive


@pytest.fixture
def populated_archive_with_releases(tmp_archive, artist_with_releases):
    """Temp archive with one artist and one existing release."""
    tmp_archive.write_text(json.dumps([
        {
            "name": artist_with_releases.name,
            "browse_id": artist_with_releases.browse_id,
            "releases": artist_with_releases.releases,
        }
    ]))
    return tmp_archive
