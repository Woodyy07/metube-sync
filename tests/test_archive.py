import json
import pytest
from src.archive import (
    Artist,
    _load,
    _save,
    load_archive,
    load_artist,
    add_releases,
    add,
    remove,
)


# ── _load ─────────────────────────────────────────────────────────────────────

def test_load_missing_file(tmp_archive):
    assert _load() == []


def test_load_empty_file(tmp_archive):
    tmp_archive.write_text("")
    assert _load() == []


def test_load_whitespace_only(tmp_archive):
    tmp_archive.write_text("   \n  ")
    assert _load() == []


def test_load_single_artist(tmp_archive):
    tmp_archive.write_text(json.dumps([
        {"name": "Lekkerfaces", "browse_id": "UC123", "releases": []}
    ]))
    result = _load()
    assert len(result) == 1
    assert isinstance(result[0], Artist)
    assert result[0].name == "Lekkerfaces"
    assert result[0].browse_id == "UC123"
    assert result[0].releases == []


def test_load_preserves_releases(tmp_archive):
    tmp_archive.write_text(json.dumps([
        {"name": "X", "browse_id": "UC1", "releases": ["url1", "url2"]}
    ]))
    result = _load()
    assert result[0].releases == ["url1", "url2"]


def test_load_multiple_artists(tmp_archive):
    tmp_archive.write_text(json.dumps([
        {"name": "Artist A", "browse_id": "UC001", "releases": []},
        {"name": "Artist B", "browse_id": "UC002", "releases": ["url1"]},
    ]))
    result = _load()
    assert len(result) == 2


# ── _save ─────────────────────────────────────────────────────────────────────

def test_save_creates_file(tmp_archive):
    _save([Artist("Lekkerfaces", "UC123", [])])
    assert tmp_archive.exists()
    content = json.loads(tmp_archive.read_text())
    assert content[0]["name"] == "Lekkerfaces"


def test_save_creates_parent_directory(tmp_path, monkeypatch):
    nested = tmp_path / "a" / "b" / "archive.json"
    monkeypatch.setattr("src.archive.ARCHIVE", nested)
    _save([Artist("X", "UC1", [])])
    assert nested.exists()


def test_save_overwrites_existing(tmp_archive):
    _save([Artist("First", "UC1", [])])
    _save([Artist("Second", "UC2", [])])
    content = json.loads(tmp_archive.read_text())
    assert len(content) == 1
    assert content[0]["name"] == "Second"


def test_save_roundtrip(tmp_archive):
    artists = [
        Artist("Artist A", "UC001", ["url1"]),
        Artist("Artist B", "UC002", []),
    ]
    _save(artists)
    loaded = _load()
    assert len(loaded) == 2
    assert loaded[0].releases == ["url1"]
    assert loaded[1].releases == []


# ── load_archive ──────────────────────────────────────────────────────────────

def test_load_archive_empty(tmp_archive):
    assert load_archive() == []


def test_load_archive_returns_list_of_artists(populated_archive):
    result = load_archive()
    assert len(result) == 1
    assert isinstance(result[0], Artist)


# ── load_artist ───────────────────────────────────────────────────────────────

def test_load_artist_found(populated_archive):
    result = load_artist("UC123")
    assert result is not None
    assert result.name == "Lekkerfaces"


def test_load_artist_not_found_returns_none(tmp_archive):
    result = load_artist("UC999")
    assert result is None


def test_load_artist_not_found_in_populated_archive(populated_archive):
    result = load_artist("UC999")
    assert result is None


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_new_artist_returns_true(tmp_archive, artist):
    assert add(artist) is True


def test_add_new_artist_persists(tmp_archive, artist):
    add(artist)
    assert len(_load()) == 1
    assert _load()[0].browse_id == "UC123"


def test_add_duplicate_returns_false(tmp_archive, artist):
    add(artist)
    assert add(artist) is False


def test_add_duplicate_does_not_duplicate(tmp_archive, artist):
    add(artist)
    add(artist)
    assert len(_load()) == 1


def test_add_multiple_different_artists(tmp_archive):
    add(Artist("Artist A", "UC001", []))
    add(Artist("Artist B", "UC002", []))
    assert len(_load()) == 2


def test_add_initializes_empty_releases(tmp_archive, artist):
    add(artist)
    assert _load()[0].releases == []


# ── remove ────────────────────────────────────────────────────────────────────

def test_remove_existing_returns_true(populated_archive):
    assert remove("UC123") is True


def test_remove_existing_deletes_artist(populated_archive):
    remove("UC123")
    assert _load() == []


def test_remove_nonexistent_returns_false(tmp_archive):
    assert remove("UC999") is False


def test_remove_nonexistent_from_populated_returns_false(populated_archive):
    assert remove("UC999") is False


def test_remove_does_not_affect_others(tmp_archive):
    add(Artist("Artist A", "UC001", []))
    add(Artist("Artist B", "UC002", []))
    remove("UC001")
    remaining = _load()
    assert len(remaining) == 1
    assert remaining[0].browse_id == "UC002"


# ── add_releases ──────────────────────────────────────────────────────────────

def test_add_releases_appends_url(populated_archive):
    add_releases("UC123", ["https://music.youtube.com/playlist?list=OLAK_new"])
    artist = load_artist("UC123")
    assert "https://music.youtube.com/playlist?list=OLAK_new" in artist.releases


def test_add_releases_multiple_urls(populated_archive):
    urls = [
        "https://music.youtube.com/playlist?list=OLAK_1",
        "https://music.youtube.com/playlist?list=OLAK_2",
    ]
    add_releases("UC123", urls)
    artist = load_artist("UC123")
    assert len(artist.releases) == 2


def test_add_releases_skips_duplicates(populated_archive):
    url = "https://music.youtube.com/playlist?list=OLAK_dup"
    add_releases("UC123", [url])
    add_releases("UC123", [url])
    artist = load_artist("UC123")
    assert artist.releases.count(url) == 1


def test_add_releases_artist_not_found_raises(tmp_archive):
    with pytest.raises(ValueError, match="UC999"):
        add_releases("UC999", ["some_url"])


def test_add_releases_does_not_affect_other_artists(tmp_archive):
    add(Artist("Artist A", "UC001", []))
    add(Artist("Artist B", "UC002", []))
    add_releases("UC001", ["url_a"])
    assert load_artist("UC002").releases == []
