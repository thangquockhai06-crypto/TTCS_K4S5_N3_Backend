import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.services.avatar_service import MAX_AVATAR_BYTES


@pytest.fixture(autouse=True)
def avatar_storage_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "AVATAR_STORAGE_DIR", str(tmp_path))
    return tmp_path


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def image_bytes(image_format: str, size: tuple[int, int] = (320, 200)) -> bytes:
    mode = "RGBA" if image_format == "PNG" else "RGB"
    image = Image.new(mode, size, (40, 120, 220, 180) if mode == "RGBA" else (40, 120, 220))
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def avatar_path(tmp_path: Path, url: str) -> Path:
    return tmp_path / "avatars" / url.rsplit("/", 1)[-1]


@pytest.mark.parametrize(
    ("filename", "content_type", "image_format"),
    [
        ("avatar.jpg", "image/jpeg", "JPEG"),
        ("avatar.png", "image/png", "PNG"),
    ],
)
def test_upload_valid_avatar_returns_square_and_thumbnail(
    client: TestClient,
    seed_data: dict,
    tmp_path: Path,
    filename: str,
    content_type: str,
    image_format: str,
):
    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": (filename, image_bytes(image_format), content_type)},
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["avatarUrl"]
    assert payload["avatarThumbnailUrl"]

    avatar_file = avatar_path(tmp_path, payload["avatarUrl"])
    thumbnail_file = avatar_path(tmp_path, payload["avatarThumbnailUrl"])
    with Image.open(avatar_file) as image:
        assert image.size == (200, 200)
        assert image.format == image_format
    with Image.open(thumbnail_file) as thumbnail:
        assert thumbnail.size == (128, 128)
        assert thumbnail.format == image_format


def test_upload_rejects_mismatched_and_unsupported_files(client: TestClient, seed_data: dict):
    cases = [
        ("renamed.exe.jpg", b"MZ" + os.urandom(64), "image/jpeg"),
        ("document.jpg", b"%PDF-1.7 fake", "image/jpeg"),
        ("animation.gif", b"GIF89a" + os.urandom(64), "image/gif"),
        ("image.webp", b"RIFF" + os.urandom(64), "image/webp"),
    ]

    for filename, content, content_type in cases:
        response = client.post(
            "/api/v1/users/me/avatar",
            files={"file": (filename, content, content_type)},
            headers=auth_header(seed_data["tokens"]["emp_a"]),
        )
        assert response.status_code == 422
        assert response.json()["detail"]


def test_upload_rejects_files_over_2mb_and_accepts_file_under_limit(
    client: TestClient, seed_data: dict
):
    oversized = image_bytes("JPEG") + b"x" * (MAX_AVATAR_BYTES + 1)
    too_large_response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("large.jpg", oversized, "image/jpeg")},
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )
    assert too_large_response.status_code == 413
    assert "2 MB" in too_large_response.json()["detail"]

    large_valid_image = Image.new("RGB", (1000, 1000))
    large_valid_image.putdata([(index % 255, (index * 7) % 255, (index * 13) % 255) for index in range(1000000)])
    output = io.BytesIO()
    large_valid_image.save(output, format="JPEG", quality=95)
    under_limit = output.getvalue()
    assert len(under_limit) < MAX_AVATAR_BYTES

    accepted_response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("under-limit.jpg", under_limit, "image/jpeg")},
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )
    assert accepted_response.status_code == 200


@pytest.mark.parametrize("size", [(400, 200), (200, 400)])
def test_upload_center_crops_landscape_and_portrait(
    client: TestClient,
    seed_data: dict,
    tmp_path: Path,
    size: tuple[int, int],
):
    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.jpg", image_bytes("JPEG", size), "image/jpeg")},
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )

    assert response.status_code == 200
    with Image.open(avatar_path(tmp_path, response.json()["avatarUrl"])) as image:
        assert image.width == image.height == min(size)


def test_upload_replaces_and_deletes_previous_files(
    client: TestClient, seed_data: dict, tmp_path: Path
):
    headers = auth_header(seed_data["tokens"]["emp_a"])
    first = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("first.jpg", image_bytes("JPEG"), "image/jpeg")},
        headers=headers,
    ).json()
    old_avatar = avatar_path(tmp_path, first["avatarUrl"])
    old_thumbnail = avatar_path(tmp_path, first["avatarThumbnailUrl"])
    assert old_avatar.exists()
    assert old_thumbnail.exists()

    second_response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("second.png", image_bytes("PNG"), "image/png")},
        headers=headers,
    )
    assert second_response.status_code == 200
    second = second_response.json()
    assert not old_avatar.exists()
    assert not old_thumbnail.exists()
    assert avatar_path(tmp_path, second["avatarUrl"]).exists()
    assert avatar_path(tmp_path, second["avatarThumbnailUrl"]).exists()


def test_avatar_upload_requires_authentication(client: TestClient):
    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.jpg", image_bytes("JPEG"), "image/jpeg")},
    )
    assert response.status_code == 401


def test_customer_responses_include_assigned_user_avatar_thumbnail(
    client: TestClient, seed_data: dict, tmp_path: Path, db_session: Session
):
    upload_response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("owner.png", image_bytes("PNG"), "image/png")},
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )
    thumbnail_url = upload_response.json()["avatarThumbnailUrl"]

    detail_response = client.get(
        f"/api/v1/customers/{seed_data['customers']['cust_a'].id}",
        headers=auth_header(seed_data["tokens"]["emp_a"]),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["assignedUser"]["id"] == seed_data["users"]["emp_a"].id
    assert detail["assignedUser"]["avatarThumbnailUrl"] == thumbnail_url

    list_response = client.get(
        "/api/v1/customers", headers=auth_header(seed_data["tokens"]["emp_a"])
    )
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json() if item["id"] == "cust-emp-a")
    assert listed["assignedUser"]["avatarThumbnailUrl"] == thumbnail_url

    null_response = client.get(
        f"/api/v1/customers/{seed_data['customers']['cust_b'].id}",
        headers=auth_header(seed_data["tokens"]["emp_b"]),
    )
    assert null_response.status_code == 200
    assert null_response.json()["assignedUser"]["avatarThumbnailUrl"] is None
