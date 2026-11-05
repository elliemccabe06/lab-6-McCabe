import pytest
from app.routers.artworks import CONFLICT_DETAIL

def test_get_seeded_artwork_empty(client):
    response = client.get("/artworks/")
    assert response.status_code == 200
    assert response.json() == []

def test_get_seeded_artwork(client, seeded_db):
    expected = {"id": 1, **seeded_db[0]}

    response = client.get("/artworks/1")

    assert response.status_code == 200
    assert response.json() == expected

def test_create_artwork(client, sample_artwork):

    response = client.post("/artworks/", json=sample_artwork)
    
    assert response.status_code == 201

    created = response.json()

    assert isinstance(created["id"], int)

    for field, value in sample_artwork.items():
        assert created[field] == value

def create_artwork_is_saved(client, created_artwork):
    artwork_id = created_artwork()["id"]
    response = client.get(f"/artworks/{artwork_id}")
    assert response.status_code == 200
    assert response.json() == created_artwork

def test_update_artwork(client, created_artwork, updated_artwork):
    artwork_id = created_artwork()["id"]
    expected = {"id": artwork_id, **updated_artwork}

    response= client.put(f"artworks/{artwork_id}", json=updated_artwork)

    assert response.status_code == 200
    assert response.json() == expected

def test_delete_artwork(client, created_artwork):
    artwork_id = created_artwork()["id"]
    response = client.delete(f"/artworks/{artwork_id}")

    assert response.status_code ==204
    assert response.content == b""

    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code ==404

@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False)
    ],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method, "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}

def test_non_integer_id(client):

    response = client.get("/artworks/mona-lisa")

    assert response.status_code == 422

def test_create_duplicate(client, created_artwork, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)

    assert response.status_code == 409
    assert response.json() == {"detail": CONFLICT_DETAIL}

def test_create_duplicate_ignores_case(client, created_artwork, sample_artwork):
    duplicate_artwork = sample_artwork.copy()
    duplicate_artwork["title"] = duplicate_artwork["title"].upper()
    duplicate_artwork["title"] = duplicate_artwork["title"].lower()

    response = client.post("/artworks/", json=duplicate_artwork)

    assert response.status_code == 409
    assert response.json() == {"detail": CONFLICT_DETAIL}

def test_update_into_duplicate(client, seeded_db, sample_artwork):
    artwork_id = 2

    mona_lisa = seeded_db[0]

    duplicate_update = sample_artwork.copy()
    duplicate_update["title"] = mona_lisa["title"]
    duplicate_update["artist"] = mona_lisa["artist"]

    response = client.put(
        f"/artworks/{artwork_id}",
        json=duplicate_update
    )
    assert response.status_code == 409

    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Lady with an Ermine"


def test_update_same_title_and_artist_is_allowed(
    client, created_artwork, sample_artwork
):
    
    artwork_id = created_artwork()["id"]

    updated = sample_artwork.copy()
    updated["museum"] = "The Metropolitan Museum of Art"

    expected = {"id": artwork_id, **updated}


    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated
    )

    assert response.status_code == 200
    assert response.json() == expected

   
    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code == 200
    assert get_response.json() == expected

@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"],
    ids=["title", "artist", "year", "medium", "museum", "image_url"],
)
def test_create_missing_field(client, sample_artwork, missing_field):
    
    artwork = sample_artwork.copy()
    artwork.pop(missing_field)

    response = client.post("/artworks/", json=artwork)

   
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]

@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("year", 3000),
        ("year", "nineteen-oh-seven"),
        ("title", ""),
    ],
    ids=["future-year", "year-not-int", "empty-title"],
)
def test_create_invalid_value(client, sample_artwork, field, bad_value):
 
    artwork = sample_artwork.copy()
    artwork[field] = bad_value

    response = client.post("/artworks/", json=artwork)

  
    assert response.status_code == 422

@pytest.mark.parametrize(
    "params, expected_count",
    [
        ({"limit": 3}, 3),
        ({"skip": 3, "limit": 4}, 4),
        ({"limit": 0}, 0),
        ({"skip": 20, "limit": 5}, 0),
    ],
    ids=["first-three", "skip-three", "zero-limit", "past-end"],
)
def test_pagination_counts(client, seeded_db, params, expected_count):
    
    response = client.get("/artworks/", params=params)

    assert response.status_code == 200
    assert len(response.json()) == expected_count

@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"limit": 101},
    ],
    ids=["negative-skip", "limit-too-large"],
)
def test_pagination_invalid(client, params):
    
    response = client.get("/artworks/", params=params)

    
    assert response.status_code == 422

@pytest.mark.parametrize(
    "artist",
    [
        "Claude Monet",
        "monet",
        "da vinci",
        "Nobody Exists",
    ],
    ids=["full-name", "lowercase-partial", "another-partial", "no-results"],
)
def test_filter_by_artist(client, seeded_db, artist):
    expected_titles = [
        artwork["title"]
        for artwork in seeded_db
        if artist.lower() in artwork["artist"].lower()
    ]

    response = client.get("/artworks/", params={"artist": artist})

    assert response.status_code == 200

    actual_titles = [
        artwork["title"] for artwork in response.json()
    ]

    assert actual_titles == expected_titles