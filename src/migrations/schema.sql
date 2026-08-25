-- ========================================================
-- NỀN TẢNG TỔ CHỨC VÀ QUẢN LÝ CUỘC THI NHIẾP ẢNH PHIM TÍCH HỢP AI
-- (AI-powered Film Photography Contest Management Platform)
-- ========================================================

CREATE SCHEMA IF NOT EXISTS app;
SET search_path TO app, public;

-- --------------------------------------------------------
-- PHÂN HỆ 1: XÁC THỰC & PHÂN QUYỀN (AUTH & RBAC)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(512),
    bio TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.roles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.user_roles (
    user_id BIGINT REFERENCES app.users(id) ON DELETE CASCADE,
    role_id BIGINT REFERENCES app.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS app.permissions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.role_permissions (
    role_id BIGINT REFERENCES app.roles(id) ON DELETE CASCADE,
    permission_id BIGINT REFERENCES app.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- --------------------------------------------------------
-- PHÂN HỆ 2: QUẢN LÝ CUỘC THI ẢNH PHIM (CONTESTS)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.contests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    rules TEXT,
    banner_url VARCHAR(512),
    created_by BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.contest_announcements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES app.contests(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_by BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.contest_settings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL UNIQUE REFERENCES app.contests(id) ON DELETE CASCADE,
    allow_public_vote BOOLEAN NOT NULL DEFAULT FALSE,
    allow_submission BOOLEAN NOT NULL DEFAULT TRUE,
    max_submission_per_user INT NOT NULL DEFAULT 1,
    scoring_mode VARCHAR(50) NOT NULL DEFAULT 'weighted',
    judges_visible BOOLEAN NOT NULL DEFAULT FALSE,
    announcement_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.rounds (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES app.contests(id) ON DELETE CASCADE,
    round_number INT NOT NULL DEFAULT 1,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    weight NUMERIC(5,2) DEFAULT 1.00,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.criteria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES app.rounds(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    max_score NUMERIC(5,2) NOT NULL DEFAULT 10.00,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- PHÂN HỆ 3: BÀI THI & THÔNG SỐ ẢNH PHIM (FILM SUBMISSIONS)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.submissions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES app.rounds(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    story_description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'submitted',
    final_score NUMERIC(5,2),
    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_round_photo UNIQUE (round_id, user_id, title)
);

CREATE TABLE IF NOT EXISTS app.submission_files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    image_hd_url VARCHAR(512) NOT NULL,
    thumbnail_url VARCHAR(512),
    width_px INT,
    height_px INT,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64) NOT NULL,
    phash VARCHAR(64),
    ahash VARCHAR(64),
    file_type VARCHAR(50) DEFAULT 'main_image' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.submission_film_metadata (
    submission_id BIGINT PRIMARY KEY REFERENCES app.submissions(id) ON DELETE CASCADE,
    film_stock VARCHAR(100) NOT NULL,
    film_iso INT,
    camera_body VARCHAR(100),
    lens VARCHAR(100),
    lab_name VARCHAR(150),
    scanner_info VARCHAR(150),
    development_process VARCHAR(50) DEFAULT 'C-41',
    taken_at_location VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.submission_reviews (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    reviewer_id BIGINT REFERENCES app.users(id) ON DELETE SET NULL,
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    review_notes TEXT,
    decision_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- PHÂN HỆ 4: PHÂN CONG & CHẤM ĐIỂM GIÁM KHẢO (SCORING)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.judge_assignments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES app.rounds(id) ON DELETE CASCADE,
    submission_id BIGINT REFERENCES app.submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'assigned',
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.scores (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    criteria_id BIGINT NOT NULL REFERENCES app.criteria(id) ON DELETE CASCADE,
    score_value NUMERIC(5,2) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_judge_criteria_score UNIQUE (submission_id, judge_id, criteria_id)
);

CREATE TABLE IF NOT EXISTS app.score_feedbacks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    general_comment TEXT NOT NULL,
    is_finalized BOOLEAN NOT NULL DEFAULT FALSE,
    summary_feedback TEXT,
    final_recommendation VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_judge_submission_feedback UNIQUE (submission_id, judge_id)
);

-- --------------------------------------------------------
-- PHÂN HỆ 5: AI MODULE (AI-GENERATED DETECTION & TAGGING)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.ai_flags (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL,
    confidence_score NUMERIC(5,2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reviewed_by BIGINT REFERENCES app.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.ai_analysis_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    ai_flag_id BIGINT REFERENCES app.ai_flags(id) ON DELETE SET NULL,
    ai_model_name VARCHAR(50) NOT NULL,
    ai_confidence_score NUMERIC(5,2),
    similarity_matched_submission_id BIGINT REFERENCES app.submissions(id) ON DELETE SET NULL,
    raw_details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.submission_ai_tags (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL,
    confidence NUMERIC(5,2) DEFAULT 90.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_submission_tag UNIQUE (submission_id, tag_name)
);

-- --------------------------------------------------------
-- PHÂN HỆ 6: TRIỂN LÃM TRỰC TUYẾN & ARCHIVE (DIGITAL ARCHIVE)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS app.digital_archive_exhibits (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES app.contests(id) ON DELETE CASCADE,
    submission_id BIGINT NOT NULL REFERENCES app.submissions(id) ON DELETE CASCADE,
    award_title VARCHAR(100),
    display_order INT DEFAULT 0,
    views_count INT DEFAULT 0,
    likes_count INT DEFAULT 0,
    published_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_exhibit_submission UNIQUE (contest_id, submission_id)
);

CREATE TABLE IF NOT EXISTS app.notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    contest_id BIGINT REFERENCES app.contests(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'info',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS app.audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES app.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_name VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Compatibility for older deployments that created submission_reviews partially.
ALTER TABLE app.submission_reviews
    ADD COLUMN IF NOT EXISTS submission_id BIGINT REFERENCES app.submissions(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS reviewer_id BIGINT REFERENCES app.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS review_notes TEXT,
    ADD COLUMN IF NOT EXISTS decision_reason TEXT;

ALTER TABLE app.contest_settings
    ADD COLUMN IF NOT EXISTS contest_id BIGINT REFERENCES app.contests(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS allow_public_vote BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS allow_submission BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS max_submission_per_user INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS scoring_mode VARCHAR(50) NOT NULL DEFAULT 'weighted',
    ADD COLUMN IF NOT EXISTS judges_visible BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS announcement_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.ai_flags
    ADD COLUMN IF NOT EXISTS review_notes VARCHAR(512),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.contest_announcements
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.digital_archive_exhibits
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.judge_assignments
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.score_feedbacks
    ADD COLUMN IF NOT EXISTS summary_feedback TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS final_recommendation VARCHAR(50),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE app.submission_files
    ADD COLUMN IF NOT EXISTS phash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS ahash VARCHAR(64);

-- INDEXES HỖ TRỢ TRUY VẤN CỰC NHANH
CREATE INDEX IF NOT EXISTS idx_film_metadata_stock ON app.submission_film_metadata(film_stock);
CREATE INDEX IF NOT EXISTS idx_film_metadata_camera ON app.submission_film_metadata(camera_body);
CREATE INDEX IF NOT EXISTS idx_submissions_round_user ON app.submissions(round_id, user_id);
CREATE INDEX IF NOT EXISTS idx_ai_flags_submission ON app.ai_flags(submission_id);
CREATE INDEX IF NOT EXISTS idx_submission_ai_tags_tag ON app.submission_ai_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_archive_exhibits_contest ON app.digital_archive_exhibits(contest_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON app.notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_submission_reviews_submission ON app.submission_reviews(submission_id);
CREATE INDEX IF NOT EXISTS idx_contest_settings_contest ON app.contest_settings(contest_id);
