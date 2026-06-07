import pytest
from unittest.mock import MagicMock, patch
from src.archive import Artist
from src.releases import get_new_releases


# ── Helpers ───────────────────────────────────────────────────────────────────

URL_1 = "https://music.youtube.com/playlist?list=OLAK_album1"
URL_2 = "https://music.youtube.com/playlist?list=OLAK_single1"

# What get_artist() returns when no params (all results already in response)
ARTIST_NO_PARAMS = {
    "albums": {
        "browseId": "UCxxx",
        "params": None,
        "results": [
            {"browseId": "MPREb_album1", "title": "Steam Power", "year": "2025"},
        ],
    },
    "singles": {
        "browseId": "UCxxx",
        "params": None,
        "results": [
            {"browseId": "MPREb_single1", "title": "BKJN", "year": "2025"},
        ],
    },
}

# What get_artist() returns when params present (pagination needed for singles)
ARTIST_WITH_PARAMS = {
    "albums": {
        "browseId": "UCxxx",
        "params": None,
        "results": [
            {"browseId": "MPREb_album1", "title": "Steam Power", "year": "2025"},
        ],
    },
    "singles": {
        "browseId": "UCxxx",
        "params": "Eg_pagination_token",
        "results": [],
    },
}

# get_album() response (no params branch — uses audioPlaylistId)
ALBUM_RESPONSE = {"audioPlaylistId": "OLAK_album1", "title": "Steam Power", "year": "2025"}
SINGLE_RESPONSE = {"audioPlaylistId": "OLAK_single1", "title": "BKJN", "year": "2025"}

# get_artist_albums() response (params branch — uses playlistId)
ARTIST_ALBUMS_RESPONSE = [
    {"playlistId": "OLAK_single1", "title": "BKJN", "year": "2025"},
    {"playlistId": "OLAK_single2", "title": "Machinery", "year": "2025"},
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_yt(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("src.releases.yt", mock)
    return mock


@pytest.fixture
def mock_load_artist(monkeypatch):
    """Returns a factory: call with the Artist to return (or None)."""
    def factory(artist):
        monkeypatch.setattr("src.releases.load_artist", lambda _: artist)
    return factory


# ── Artist not in archive ─────────────────────────────────────────────────────

def test_returns_empty_when_artist_not_in_archive(mock_load_artist, mock_yt):
    mock_load_artist(None)
    result = get_new_releases("UC123")
    assert result == []
    mock_yt.get_artist.assert_not_called()


# ── API errors ────────────────────────────────────────────────────────────────

def test_raises_runtime_error_on_get_artist_failure(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.side_effect = Exception("API down")
    with pytest.raises(RuntimeError, match="Could not fetch artist"):
        get_new_releases("UC123")


def test_raises_runtime_error_on_get_artist_albums_failure(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_WITH_PARAMS
    mock_yt.get_artist_albums.side_effect = Exception("API down")
    with pytest.raises(RuntimeError, match="Could not fetch singles"):
        get_new_releases("UC123")


def test_raises_runtime_error_on_get_album_failure(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = Exception("API down")
    with pytest.raises(RuntimeError, match="Could not fetch albums"):
        get_new_releases("UC123")


# ── No params branch (get_album called per result) ───────────────────────────

def test_no_params_calls_get_album_for_each_result(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    get_new_releases("UC123")

    assert mock_yt.get_album.call_count == 2


def test_no_params_uses_audio_playlist_id(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")
    urls = [r["url"] for r in results]

    assert URL_1 in urls
    assert URL_2 in urls


# ── Params branch (get_artist_albums called) ─────────────────────────────────

def test_params_calls_get_artist_albums(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_WITH_PARAMS
    mock_yt.get_album.return_value = ALBUM_RESPONSE
    mock_yt.get_artist_albums.return_value = ARTIST_ALBUMS_RESPONSE

    get_new_releases("UC123")

    mock_yt.get_artist_albums.assert_called_once_with("UCxxx", "Eg_pagination_token", limit=None)


def test_params_uses_playlist_id(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_WITH_PARAMS
    mock_yt.get_album.return_value = ALBUM_RESPONSE
    mock_yt.get_artist_albums.return_value = ARTIST_ALBUMS_RESPONSE

    results = get_new_releases("UC123")
    urls = [r["url"] for r in results]

    assert "https://music.youtube.com/playlist?list=OLAK_single1" in urls
    assert "https://music.youtube.com/playlist?list=OLAK_single2" in urls


# ── Archive filtering ─────────────────────────────────────────────────────────

def test_filters_out_already_archived_url(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", releases=[URL_1]))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")
    urls = [r["url"] for r in results]

    assert URL_1 not in urls
    assert URL_2 in urls


def test_all_archived_returns_empty(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", releases=[URL_1, URL_2]))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")
    assert results == []


def test_no_archived_returns_all(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", releases=[]))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")
    assert len(results) == 2


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_has_required_fields(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")

    for r in results:
        assert "title" in r
        assert "year" in r
        assert "url" in r
        assert "category" in r


def test_result_category_values(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    mock_yt.get_album.side_effect = [ALBUM_RESPONSE, SINGLE_RESPONSE]

    results = get_new_releases("UC123")
    categories = {r["category"] for r in results}

    assert categories <= {"albums", "singles"}


def test_skips_release_with_no_playlist_id(mock_load_artist, mock_yt):
    mock_load_artist(Artist("Lekkerfaces", "UC123", []))
    mock_yt.get_artist.return_value = ARTIST_NO_PARAMS
    # Return album with no playlistId or audioPlaylistId
    mock_yt.get_album.side_effect = [
        {"title": "No ID Album", "year": "2025"},  # missing playlist ID
        SINGLE_RESPONSE,
    ]

    results = get_new_releases("UC123")
    assert len(results) == 1
    assert results[0]["title"] == "BKJN"
