import os
import sys
import io
import contextlib
import atexit
import tempfile
from pathlib import Path
from sqlalchemy.orm import close_all_sessions

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Independent SQLite file for testing
DB_FILE = Path(tempfile.gettempdir()) / (
    f'flask_clean_architecture_duplicate_{os.getpid()}.db'
)
DB_FILE.unlink(missing_ok=True)
os.environ['POSTGREE_DATABASE_URL'] = f'sqlite:///{DB_FILE.as_posix()}'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models import *

def cleanup_test_database():
    try:
        database = db_factory.get_database("POSTGREE")
        close_all_sessions()
        database.engine.dispose()
    finally:
        try:
            DB_FILE.unlink(missing_ok=True)
        except PermissionError:
            pass

atexit.register(cleanup_test_database)

# Setup schemas
engine = db_factory.get_database("POSTGREE").engine
Base.metadata.create_all(engine)

from sqlalchemy import text
from services.duplicate_detection_service import DuplicateDetectionService
from services.submission_service import SubmissionService
from infrastructure.repositories.submission_repository import SubmissionRepository

def test_duplicate_submission_integration():
    """
    Verify:
    1. Uploading/creating a submission calculates and stores phash/ahash.
    2. Uploading a second, identical submission triggers AI flag 'duplicate_similarity' and report.
    """
    repo = SubmissionRepository()
    service = SubmissionService(submission_repo=repo)
    dup_service = DuplicateDetectionService()
    session = repo.session

    # Seed minimum dependencies
    session.execute(text("INSERT INTO roles (code, name) VALUES ('participant', 'Participant')"))
    session.execute(text("INSERT INTO users (username, email, password_hash, status) VALUES ('part1', 'p1@ex.com', 'hash', 'active')"))
    user_id = session.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    
    session.execute(text("INSERT INTO contests (title, slug, created_by, status) VALUES ('Contest 1', 'c1', :uid, 'published')"), {"uid": user_id})
    contest_id = session.execute(text("SELECT id FROM contests LIMIT 1")).scalar()
    
    session.execute(text("INSERT INTO rounds (contest_id, round_number, title, status) VALUES (:cid, 1, 'Round 1', 'open')"), {"cid": contest_id})
    round_id = session.execute(text("SELECT id FROM rounds LIMIT 1")).scalar()
    session.commit()

    # Load test image bytes
    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_images'))
    image_files = sorted([
        f for f in os.listdir(image_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])
    image_path = os.path.join(image_dir, image_files[0])
    with open(image_path, 'rb') as f:
        img_bytes = f.read()

    # 1. Create first submission
    files_list = [{"file_bytes": img_bytes, "filename": "first.jpg", "content_type": "image/jpeg"}]
    sub1 = service.create_submission(
        round_id=round_id,
        user_id=user_id,
        title="First submission",
        files=files_list,
        film_metadata={"film_stock": "Kodak Gold 200"},
        status="submitted"
    )

    # Check phash/ahash got saved in DB
    sub_file1 = session.query(SubmissionFileModel).filter_by(submission_id=sub1.id).first()
    assert sub_file1.phash is not None
    assert sub_file1.ahash is not None
    print("Submission 1 saved with phash:", sub_file1.phash, "ahash:", sub_file1.ahash)

    # 2. Create second submission (duplicate image)
    sub2 = service.create_submission(
        round_id=round_id,
        user_id=user_id,
        title="Second submission",
        files=files_list,
        film_metadata={"film_stock": "Kodak Gold 200"},
        status="submitted"
    )

    # Check duplicate flags
    ai_flag = session.query(AIFlagModel).filter_by(submission_id=sub2.id, flag_type="duplicate_similarity").first()
    assert ai_flag is not None
    assert ai_flag.risk_level == "high"
    print("AI Flag saved successfully for duplicate:", ai_flag.confidence_score, "risk:", ai_flag.risk_level)

    # Check report
    report = session.query(AIAnalysisReportModel).filter_by(submission_id=sub2.id, ai_model_name="Duplicate Detection Engine").first()
    assert report is not None
    assert report.similarity_matched_submission_id == sub1.id
    print("AI Report matching submission ID:", report.similarity_matched_submission_id)

    # Check API-like direct call
    api_result = dup_service.check_duplicate_against_database(img_bytes, exclude_submission_id=sub1.id, session=session)
    assert api_result["similarity_score"] == 100.0
    assert api_result["is_duplicate"] is True
    assert api_result["matched_submission_id"] == sub2.id
    print("API checking returned similarity:", api_result["similarity_score"])

if __name__ == '__main__':
    test_duplicate_submission_integration()
