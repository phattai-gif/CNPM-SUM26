import os
import sys
from datetime import datetime, timezone

# Add src to sys.path
SRC_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../src")
)
sys.path.insert(0, SRC_PATH)

from app import create_app
from infrastructure.databases.factory_database import (
    FactoryDatabase as db_factory,
)
from infrastructure.models.app import (
    ContestModel,
    DigitalArchiveExhibitModel,
    RoundModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    SubmissionModel,
    UserModel,
)


def get_session(app):
    """
    Get database session for testing.
    """
    with app.app_context():
        return db_factory.get_database("POSTGREE").session


def setup_gallery_test_data(session):
    """
    Idempotent helper to seed test data for gallery API tests.

    The function can be executed multiple times without creating
    duplicate test data.
    """
    try:
        # ============================================================
        # 1. Create test user
        # ============================================================
        user = (
            session.query(UserModel)
            .filter_by(username="gallery_user")
            .first()
        )

        if not user:
            user = UserModel(
                username="gallery_user",
                email="gallery_user@example.com",
                password_hash="hashed_pw",
                full_name="Gallery Tester",
            )
            session.add(user)
            session.commit()

        # ============================================================
        # 2. Create Contest 2026
        # ============================================================
        contest1 = (
            session.query(ContestModel)
            .filter_by(slug="contest-2026")
            .first()
        )

        if not contest1:
            contest1 = ContestModel(
                title="Contest 2026",
                slug="contest-2026",
                created_by=user.id,
                status="published",
                start_date=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
            )
            session.add(contest1)
            session.commit()

        # ============================================================
        # 3. Create Contest 2025
        # ============================================================
        contest2 = (
            session.query(ContestModel)
            .filter_by(slug="contest-2025")
            .first()
        )

        if not contest2:
            contest2 = ContestModel(
                title="Contest 2025",
                slug="contest-2025",
                created_by=user.id,
                status="published",
                start_date=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
            )
            session.add(contest2)
            session.commit()

        # ============================================================
        # 4. Create Round 1 - Contest 2026
        # ============================================================
        round1 = (
            session.query(RoundModel)
            .filter_by(
                contest_id=contest1.id,
                title="Round 1 2026",
            )
            .first()
        )

        if not round1:
            round1 = RoundModel(
                contest_id=contest1.id,
                round_number=1,
                title="Round 1 2026",
            )
            session.add(round1)
            session.commit()

        # ============================================================
        # 5. Create Round 1 - Contest 2025
        # ============================================================
        round2 = (
            session.query(RoundModel)
            .filter_by(
                contest_id=contest2.id,
                title="Round 1 2025",
            )
            .first()
        )

        if not round2:
            round2 = RoundModel(
                contest_id=contest2.id,
                round_number=1,
                title="Round 1 2025",
            )
            session.add(round2)
            session.commit()

        # ============================================================
        # 6. Submission: Sunset in Hanoi
        # ============================================================
        sub1 = (
            session.query(SubmissionModel)
            .filter_by(title="Sunset in Hanoi")
            .first()
        )

        if not sub1:
            sub1 = SubmissionModel(
                round_id=round1.id,
                user_id=user.id,
                title="Sunset in Hanoi",
                status="published",
                final_score=9.5,
                created_at=datetime(
                    2026,
                    3,
                    15,
                    12,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
                submitted_at=datetime(
                    2026,
                    3,
                    15,
                    12,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
            )

            session.add(sub1)
            session.commit()

            file1 = SubmissionFileModel(
                submission_id=sub1.id,
                image_hd_url="https://example.com/img1_hd.jpg",
                thumbnail_url="https://example.com/img1_thumb.jpg",
                file_hash="hash1",
                file_type="main_image",
            )

            meta1 = SubmissionFilmMetadataModel(
                submission_id=sub1.id,
                film_stock="Kodak Portra 400",
                camera_body="Fujifilm X100V",
            )

            exhibit1 = DigitalArchiveExhibitModel(
                contest_id=contest1.id,
                submission_id=sub1.id,
                award_title="Gold Prize",
            )

            session.add_all(
                [
                    file1,
                    meta1,
                    exhibit1,
                ]
            )
            session.commit()

        # ============================================================
        # 7. Submission: Old Quarter Alley
        # ============================================================
        sub2 = (
            session.query(SubmissionModel)
            .filter_by(title="Old Quarter Alley")
            .first()
        )

        if not sub2:
            sub2 = SubmissionModel(
                round_id=round1.id,
                user_id=user.id,
                title="Old Quarter Alley",
                status="approved",
                final_score=8.7,
                created_at=datetime(
                    2026,
                    4,
                    10,
                    10,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
                submitted_at=datetime(
                    2026,
                    4,
                    10,
                    10,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
            )

            session.add(sub2)
            session.commit()

            file2 = SubmissionFileModel(
                submission_id=sub2.id,
                image_hd_url="https://example.com/img2_hd.jpg",
                thumbnail_url="https://example.com/img2_thumb.jpg",
                file_hash="hash2",
                file_type="main_image",
            )

            meta2 = SubmissionFilmMetadataModel(
                submission_id=sub2.id,
                film_stock="Ilford HP5 Plus",
                camera_body="Leica M6",
            )

            session.add_all(
                [
                    file2,
                    meta2,
                ]
            )
            session.commit()

        # ============================================================
        # 8. Submission: Saigon River Dusk
        # ============================================================
        sub3 = (
            session.query(SubmissionModel)
            .filter_by(title="Saigon River Dusk")
            .first()
        )

        if not sub3:
            sub3 = SubmissionModel(
                round_id=round2.id,
                user_id=user.id,
                title="Saigon River Dusk",
                status="published",
                final_score=9.0,
                created_at=datetime(
                    2025,
                    6,
                    20,
                    15,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
                submitted_at=datetime(
                    2025,
                    6,
                    20,
                    15,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
            )

            session.add(sub3)
            session.commit()

            file3 = SubmissionFileModel(
                submission_id=sub3.id,
                image_hd_url="https://example.com/img3_hd.jpg",
                thumbnail_url="https://example.com/img3_thumb.jpg",
                file_hash="hash3",
                file_type="main_image",
            )

            meta3 = SubmissionFilmMetadataModel(
                submission_id=sub3.id,
                film_stock="Kodak Portra 400",
                camera_body="Nikon F3",
            )

            session.add_all(
                [
                    file3,
                    meta3,
                ]
            )
            session.commit()

        # ============================================================
        # 9. Non-public submissions
        # ============================================================
        sub4 = (
            session.query(SubmissionModel)
            .filter_by(title="Draft Photo")
            .first()
        )

        if not sub4:
            sub4 = SubmissionModel(
                round_id=round1.id,
                user_id=user.id,
                title="Draft Photo",
                status="draft",
            )

            session.add(sub4)

        sub5 = (
            session.query(SubmissionModel)
            .filter_by(title="Rejected Photo")
            .first()
        )

        if not sub5:
            sub5 = SubmissionModel(
                round_id=round1.id,
                user_id=user.id,
                title="Rejected Photo",
                status="rejected",
            )

            session.add(sub5)

        sub6 = (
            session.query(SubmissionModel)
            .filter_by(title="Submitted Photo")
            .first()
        )

        if not sub6:
            sub6 = SubmissionModel(
                round_id=round1.id,
                user_id=user.id,
                title="Submitted Photo",
                status="submitted",
            )

            session.add(sub6)

        session.commit()

    except Exception:
        session.rollback()
        raise


def create_test_client():
    """
    Create Flask test client and seed gallery test data.
    """
    app = create_app()

    with app.app_context():
        session = db_factory.get_database("POSTGREE").session
        setup_gallery_test_data(session)

    return app.test_client()


# ====================================================================
# TEST 1
# ====================================================================


def test_get_public_gallery_all():
    """
    Test 1 - GET /api/gallery returns public submissions.
    """
    client = create_test_client()

    response = client.get("/api/gallery")

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data

    assert data["total"] >= 3
    assert len(data["items"]) >= 3

    item = data["items"][0]

    assert "id" in item
    assert "thumbnail_url" in item
    assert "image_hd_url" in item
    assert "title" in item
    assert "metadata" in item

    assert "film_stock" in item["metadata"]
    assert "camera_model" in item["metadata"]
    assert "year" in item["metadata"]

    assert "score" in item
    assert "is_winner" in item


# ====================================================================
# TEST 2
# ====================================================================


def test_filter_non_public_submissions():
    """
    Test 2 - Verify private/draft/rejected/submitted
    submissions are NOT returned.
    """
    client = create_test_client()

    response = client.get("/api/gallery?limit=100")

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    titles = [
        item["title"]
        for item in data["items"]
    ]

    assert "Draft Photo" not in titles
    assert "Rejected Photo" not in titles
    assert "Submitted Photo" not in titles


# ====================================================================
# TEST 3
# ====================================================================


def test_filter_film_stock():
    """
    Test 3 - Filter by film_stock.
    """
    client = create_test_client()

    response = client.get(
        "/api/gallery?film_stock=Kodak%20Portra%20400"
    )

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert data["total"] >= 2

    for item in data["items"]:
        film_stock = item["metadata"]["film_stock"]

        assert "kodak portra 400" in film_stock.lower()


# ====================================================================
# TEST 4
# ====================================================================


def test_filter_camera_model():
    """
    Test 4 - Filter by camera_model.
    """
    client = create_test_client()

    response = client.get(
        "/api/gallery?camera_model=Fujifilm%20X100V"
    )

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert data["total"] >= 1

    assert any(
        item["title"] == "Sunset in Hanoi"
        for item in data["items"]
    )

    assert any(
        item["metadata"]["camera_model"] == "Fujifilm X100V"
        for item in data["items"]
    )


# ====================================================================
# TEST 5
# ====================================================================


def test_filter_contest():
    """
    Test 5 - Filter by contest.
    """
    app = create_app()

    with app.app_context():
        session = db_factory.get_database("POSTGREE").session

        setup_gallery_test_data(session)

        contest = (
            session.query(ContestModel)
            .filter_by(slug="contest-2026")
            .first()
        )

        assert contest is not None

        contest_id = contest.id

    client = app.test_client()

    response = client.get(
        f"/api/gallery?contest={contest_id}"
    )

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert data["total"] >= 2

    for item in data["items"]:
        assert item["contest"]["id"] == contest_id


# ====================================================================
# TEST 6
# ====================================================================


def test_filter_year():
    """
    Test 6 - Filter by year.
    """
    client = create_test_client()

    response = client.get(
        "/api/gallery?year=2026"
    )

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert data["total"] >= 2

    for item in data["items"]:
        assert item["metadata"]["year"] == 2026


# ====================================================================
# TEST 7
# ====================================================================


def test_combined_filters():
    """
    Test 7 - Combined filters.
    """
    app = create_app()

    with app.app_context():
        session = db_factory.get_database("POSTGREE").session

        setup_gallery_test_data(session)

        contest = (
            session.query(ContestModel)
            .filter_by(slug="contest-2026")
            .first()
        )

        assert contest is not None

        contest_id = contest.id

    client = app.test_client()

    response = client.get(
        "/api/gallery"
        f"?film_stock=Kodak%20Portra%20400"
        f"&camera_model=Fujifilm%20X100V"
        f"&contest={contest_id}"
        f"&year=2026"
    )

    assert response.status_code == 200, (
        f"Got status {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )

    data = response.get_json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["title"] == "Sunset in Hanoi"
    assert item["is_winner"] is True


# ====================================================================
# TEST 8
# ====================================================================


def test_pagination():
    """
    Test 8 - Pagination parameters page and limit.
    """
    client = create_test_client()

    # ------------------------------------------------------------
    # Page 1
    # ------------------------------------------------------------

    response_page_1 = client.get(
        "/api/gallery?page=1&limit=2"
    )

    assert response_page_1.status_code == 200, (
        f"Got status {response_page_1.status_code}: "
        f"{response_page_1.get_data(as_text=True)}"
    )

    data_page_1 = response_page_1.get_json()

    assert data_page_1["page"] == 1
    assert data_page_1["limit"] == 2
    assert len(data_page_1["items"]) == 2

    # ------------------------------------------------------------
    # Page 2
    # ------------------------------------------------------------

    response_page_2 = client.get(
        "/api/gallery?page=2&limit=2"
    )

    assert response_page_2.status_code == 200, (
        f"Got status {response_page_2.status_code}: "
        f"{response_page_2.get_data(as_text=True)}"
    )

    data_page_2 = response_page_2.get_json()

    assert data_page_2["page"] == 2
    assert len(data_page_2["items"]) >= 1

    # ------------------------------------------------------------
    # Ensure no duplicate submissions between pages
    # ------------------------------------------------------------

    page_1_ids = {
        item["id"]
        for item in data_page_1["items"]
    }

    page_2_ids = {
        item["id"]
        for item in data_page_2["items"]
    }

    assert page_1_ids.isdisjoint(page_2_ids)


# ====================================================================
# TEST 9
# ====================================================================


def test_invalid_parameters():
    """
    Test 9 - Invalid query parameters return HTTP 400.
    """
    app = create_app()
    client = app.test_client()

    invalid_queries = [
        "/api/gallery?page=0",
        "/api/gallery?page=-1",
        "/api/gallery?page=abc",
        "/api/gallery?limit=0",
        "/api/gallery?limit=-5",
        "/api/gallery?limit=101",
        "/api/gallery?year=invalid",
        "/api/gallery?contest=invalid",
        "/api/gallery?contest=-1",
    ]

    for query in invalid_queries:
        response = client.get(query)

        assert response.status_code == 400, (
            f"Query '{query}' expected 400, "
            f"got {response.status_code}"
        )

        data = response.get_json()

        assert data is not None
        assert "message" in data