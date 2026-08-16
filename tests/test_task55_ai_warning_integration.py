import os
import sys
import io
import contextlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Dùng SQLite file để test độc lập, không cần PostgreSQL
os.environ['POSTGREE_DATABASE_URL'] = 'sqlite:///./test_task55.db'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import tất cả model để SQLAlchemy tạo đầy đủ bảng (bao gồm FK dependencies)
from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.user_model import UserModel
from infrastructure.models.contest_model import ContestModel
from infrastructure.models.round_model import RoundModel
from infrastructure.models.submission_model import SubmissionModel
from infrastructure.models.submission_file_model import SubmissionFileModel
from infrastructure.models.film_metadata_model import SubmissionFilmMetadataModel

# AIFlagModel: SQLite không hỗ trợ BigInteger autoincrement đúng cách,
# nên ta tạo bảng ai_flags thủ công bằng SQL raw cho mục đích test
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from sqlalchemy import text

engine = db_factory.get_database("POSTGREE").engine

# Tắt FK enforcement để SQLite cho phép insert test data
with engine.connect() as conn:
    conn.execute(text("PRAGMA foreign_keys = OFF"))
    conn.commit()

# Xoá bảng ai_flags nếu tồn tại (để tái tạo với INTEGER PK phù hợp SQLite)
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS ai_flags"))
    conn.commit()

Base.metadata.create_all(engine)

# Tạo lại bảng ai_flags với INTEGER PRIMARY KEY (SQLite autoincrement)
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ai_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            flag_type VARCHAR(50) NOT NULL,
            confidence_score NUMERIC(5, 2) NOT NULL,
            risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            reviewed_by INTEGER,
            reviewed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()



from infrastructure.repositories.submission_repository import SubmissionRepository
from services.ai_detection_service import AiDetectionService


def test_task55_ai_warning_integration():
    """
    Task 55 - Integrate AI warning vào workflow review:
    1. Gọi AiDetectionService phân tích ảnh -> lấy ai_score, ai_message
    2. Lưu kết quả vào bảng ai_flags trong DB
    3. Đọc lại từ DB để xác nhận đã lưu thành công
    """
    repo = SubmissionRepository()
    service = AiDetectionService()
    session = repo.session

    # Seed dữ liệu tối thiểu (tắt FK nên không cần insert user/round/submission thật)
    FAKE_SUBMISSION_ID = 9999

    # -------------------------------------------------------
    # Bước 1: Gọi AI service phân tích ảnh
    # -------------------------------------------------------
    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_images'))
    image_files = sorted([
        f for f in os.listdir(image_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])
    image_path = os.path.join(image_dir, image_files[0])

    ai_result = service.detect_ai(image_path)
    ai_score  = ai_result.get('ai_score', 0)
    ai_message = ai_result.get('ai_message', '')

    if ai_score >= 70:
        risk_level = 'high'
    elif ai_score >= 30:
        risk_level = 'medium'
    else:
        risk_level = 'safe'

    print("=== Buoc 1: Ket qua AI Service ===")
    print("file:", os.path.basename(image_path))
    print("ai_score:", ai_score)
    print("ai_message:", ai_message)
    print("risk_level:", risk_level)

    # -------------------------------------------------------
    # Bước 2: Lưu vào bảng ai_flags trong DB (raw SQL vì SQLite)
    # -------------------------------------------------------
    session.execute(text("""
        DELETE FROM ai_flags WHERE submission_id = :sid AND flag_type = 'AI_METADATA'
    """), {"sid": FAKE_SUBMISSION_ID})
    session.execute(text("""
        INSERT INTO ai_flags (submission_id, flag_type, confidence_score, risk_level, status)
        VALUES (:sid, 'AI_METADATA', :score, :risk, 'pending')
    """), {"sid": FAKE_SUBMISSION_ID, "score": float(ai_score), "risk": risk_level})
    session.commit()

    print("\n=== Buoc 2: Da luu vao DB (bang ai_flags) ===")
    print("submission_id:", FAKE_SUBMISSION_ID)
    print("confidence_score:", float(ai_score))
    print("risk_level:", risk_level)
    print("status: pending")

    # -------------------------------------------------------
    # Bước 3: Đọc lại từ DB - mô phỏng lúc Giám khảo mở bài thi
    # -------------------------------------------------------
    row = session.execute(text("""
        SELECT id, submission_id, flag_type, confidence_score, risk_level, status
        FROM ai_flags
        WHERE submission_id = :sid AND flag_type = 'AI_METADATA'
        LIMIT 1
    """), {"sid": FAKE_SUBMISSION_ID}).fetchone()

    print("\n=== Buoc 3: Doc lai tu DB (Giam khao xem bai thi) ===")
    print("id:", row[0])
    print("submission_id:", row[1])
    print("flag_type:", row[2])
    print("confidence_score:", float(row[3]))
    print("risk_level:", row[4])
    print("status:", row[5])

    # Dạng JSON mà API GET /submissions/<id> sẽ trả về cho Giám khảo
    print("\n=== JSON API tra ve cho Giam khao (ai_flag field) ===")
    print({
        "ai_score": float(row[3]),
        "ai_message": ai_message,
        "risk_level": row[4],
        "status": row[5],
    })


if __name__ == '__main__':
    test_task55_ai_warning_integration()
