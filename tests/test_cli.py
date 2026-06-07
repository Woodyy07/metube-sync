import json
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock
from src.cli import app
from src.archive import Artist, add


runner = CliRunner()

MOCK_RELEASES = [
    {
        "title": "Steam Power",
        "year": "2025",
        "url": "https://music.youtube.com/playlist?list=OLAK_1",
        "category": "albums",
    },
    {
        "title": "BKJN",
        "year": "2025",
        "url": "https://music.youtube.com/playlist?list=OLAK_2",
        "category": "singles",
    },
]

MOCK_SEARCH_RESULTS = [
    {"artist": "Lekkerfaces", "browseId": "UC123", "subscribers": "10K"},
    {"artist": "Other Artist", "browseId": "UC456", "subscribers": "5K"},
]


# ── list ──────────────────────────────────────────────────────────────────────

def test_list_empty_archive(tmp_archive):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No artists followed yet" in result.output


def test_list_shows_artists(populated_archive):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Lekkerfaces" in result.output
    assert "UC123" in result.output


def test_list_shows_count(tmp_archive):
    add(Artist("Artist A", "UC001", []))
    add(Artist("Artist B", "UC002", []))
    result = runner.invoke(app, ["list"])
    assert "2 artist(s)" in result.output


# ── remove ────────────────────────────────────────────────────────────────────

def test_remove_empty_archive(tmp_archive):
    result = runner.invoke(app, ["remove", "lekkerfaces"])
    assert "No artists followed yet" in result.output


def test_remove_not_found(populated_archive):
    result = runner.invoke(app, ["remove", "unknown"])
    assert result.exit_code == 1
    assert "No artist matching" in result.output


def test_remove_confirmed(populated_archive):
    result = runner.invoke(app, ["remove", "lekkerfaces"], input="y\n")
    assert "Removed" in result.output


def test_remove_cancelled(populated_archive):
    result = runner.invoke(app, ["remove", "lekkerfaces"], input="n\n")
    assert "Cancelled" in result.output


def test_remove_by_browse_id(populated_archive):
    result = runner.invoke(app, ["remove", "UC123"], input="y\n")
    assert "Removed" in result.output


def test_remove_actually_removes(populated_archive):
    runner.invoke(app, ["remove", "lekkerfaces"], input="y\n")
    result = runner.invoke(app, ["list"])
    assert "No artists followed yet" in result.output


def test_remove_multiple_matches_prompts_selection(tmp_archive):
    add(Artist("Lekkerfaces", "UC001", []))
    add(Artist("Lekker DJ", "UC002", []))
    result = runner.invoke(app, ["remove", "lekker"], input="1\ny\n")
    assert result.exit_code == 0


# ── check ─────────────────────────────────────────────────────────────────────

def test_check_empty_archive(tmp_archive):
    result = runner.invoke(app, ["check", "lekkerfaces"])
    assert "No artists followed yet" in result.output


def test_check_artist_not_found(populated_archive):
    result = runner.invoke(app, ["check", "unknown"])
    assert result.exit_code == 1
    assert "No artist matching" in result.output


def test_check_no_new_releases(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: [])
    result = runner.invoke(app, ["check", "lekkerfaces"])
    assert "No new releases" in result.output


def test_check_api_error(populated_archive, monkeypatch):
    def raise_error(_):
        raise RuntimeError("API down")
    monkeypatch.setattr("src.releases.get_new_releases", raise_error)
    result = runner.invoke(app, ["check", "lekkerfaces"])
    assert "API down" in result.output


def test_check_shows_releases_table(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    result = runner.invoke(app, ["check", "lekkerfaces"], input="all\nnone\n")
    assert "Steam Power" in result.output
    assert "BKJN" in result.output


def test_check_download_all_untrack_none(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    # Select all downloads, untrack none, confirm downloaded
    result = runner.invoke(app, ["check", "lekkerfaces"], input="all\nnone\ny\n")
    assert "2 release(s) to download" in result.output


def test_check_download_none_untrack_all(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    # Skip all downloads, untrack everything
    result = runner.invoke(app, ["check", "lekkerfaces"], input="all\nothers\n")


def test_check_untrack_archives_releases(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    # Download first release only, untrack the other, don't confirm download
    runner.invoke(app, ["check", "lekkerfaces"], input="1\nothers\nn\n")
    from src.archive import load_artist
    artist = load_artist("UC123")
    # Only the untracked release (index 1, BKJN) should be archived
    assert len(artist.releases) == 1
    assert "https://music.youtube.com/playlist?list=OLAK_2" in artist.releases


def test_check_download_confirm_archives_releases(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    runner.invoke(app, ["check", "lekkerfaces"], input="all\nnone\ny\n")
    from src.archive import load_artist
    artist = load_artist("UC123")
    assert len(artist.releases) == 2


def test_check_download_no_confirm_does_not_archive(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    runner.invoke(app, ["check", "lekkerfaces"], input="all\nnone\nn\n")
    from src.archive import load_artist
    artist = load_artist("UC123")
    assert artist.releases == []


def test_check_nothing_to_do(populated_archive, monkeypatch):
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: MOCK_RELEASES)
    # Download all, untrack none, don't confirm → nothing archived, nothing to do message absent
    # Download none (empty string forces invalid), but let's test the explicit path:
    # Select no downloads (empty) and no untracks
    result = runner.invoke(app, ["check", "lekkerfaces"], input="all\nnone\nn\n")
    assert result.exit_code == 0


# ── sync ──────────────────────────────────────────────────────────────────────

def test_sync_empty_archive(tmp_archive):
    result = runner.invoke(app, ["sync"])
    assert "No artists in list" in result.output


def test_sync_calls_check_for_each_artist(tmp_archive, monkeypatch):
    add(Artist("Artist A", "UC001", []))
    add(Artist("Artist B", "UC002", []))

    checked = []

    def fake_get_new_releases(browse_id):
        checked.append(browse_id)
        return []

    monkeypatch.setattr("src.releases.get_new_releases", fake_get_new_releases)
    runner.invoke(app, ["sync"])

    assert "UC001" in checked
    assert "UC002" in checked


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_no_results(tmp_archive, monkeypatch):
    monkeypatch.setattr("src.cli.yt.search", lambda *a, **kw: [])
    result = runner.invoke(app, ["add", "unknown artist"])
    assert result.exit_code == 1
    assert "No artists found" in result.output


def test_add_new_artist(tmp_archive, monkeypatch):
    monkeypatch.setattr("src.cli.yt.search", lambda *a, **kw: MOCK_SEARCH_RESULTS)
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: [])
    result = runner.invoke(app, ["add", "lekkerfaces"], input="1\n")
    assert "Now following" in result.output
    assert "Lekkerfaces" in result.output


def test_add_already_following(tmp_archive, monkeypatch):
    add(Artist("Lekkerfaces", "UC123", []))
    monkeypatch.setattr("src.cli.yt.search", lambda *a, **kw: MOCK_SEARCH_RESULTS)
    monkeypatch.setattr("src.releases.get_new_releases", lambda _: [])
    result = runner.invoke(app, ["add", "lekkerfaces"], input="1\n")
    assert "Already following" in result.output


def test_add_invalid_selection(tmp_archive, monkeypatch):
    monkeypatch.setattr("src.cli.yt.search", lambda *a, **kw: MOCK_SEARCH_RESULTS)
    result = runner.invoke(app, ["add", "lekkerfaces"], input="abc\n")
    assert result.exit_code == 1
    assert "Invalid selection" in result.output
