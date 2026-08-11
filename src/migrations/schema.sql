-- ========================================================
-- NỀN TẢNG TỔ CHỨC VÀ QUẢN LÝ CUỘC THI NHIẾP ẢNH PHIM TÍCH HỢP AI
-- (AI-powered Film Photography Contest Management Platform)
-- ========================================================

-- --------------------------------------------------------
-- PHÂN HỆ 1: XÁC THỰC & PHÂN QUYỀN (AUTH & RBAC)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
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

CREATE TABLE IF NOT EXISTS roles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE, -- 'admin', 'organizer', 'judge', 'participant'
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS permissions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE,
    permission_id BIGINT REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- --------------------------------------------------------
-- PHÂN HỆ 2: QUẢN LÝ CUỘC THI ẢNH PHIM (CONTESTS)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS contests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    rules TEXT, -- Thể lệ cuộc thi ảnh phim
    banner_url VARCHAR(512),
    created_by BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- 'draft', 'active', 'grading', 'completed'
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contest_announcements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_by BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rounds (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
    round_number INT NOT NULL DEFAULT 1,
    title VARCHAR(255) NOT NULL, -- Vd: "Vòng Sơ Loại", "Vòng Chung Kết"
    description TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    weight NUMERIC(5,2) DEFAULT 1.00,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming', -- 'upcoming', 'ongoing', 'grading', 'ended'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS criteria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- Vd: "Màu phim & Ánh sáng", "Bố cục & Khoảnh khắc", "Tính Sáng tạo"
    description TEXT,
    max_score NUMERIC(5,2) NOT NULL DEFAULT 10.00,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- PHÂN HỆ 3: BÀI THI & THÔNG SỐ ẢNH PHIM (FILM SUBMISSIONS)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS submissions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    story_description TEXT, -- Lời tự sự / Câu chuyện bức ảnh phim
    status VARCHAR(20) NOT NULL DEFAULT 'submitted', -- 'submitted', 'flagged', 'approved', 'rejected', 'evaluated'
    final_score NUMERIC(5,2), -- Điểm trung bình chốt vòng
    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_round_photo UNIQUE (round_id, user_id, title)
);

CREATE TABLE IF NOT EXISTS submission_files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    image_hd_url VARCHAR(512) NOT NULL, -- Link ảnh HD trên Supabase Storage Bucket
    thumbnail_url VARCHAR(512),         -- Link ảnh nén nhỏ hỗ trợ soi nhanh
    width_px INT,
    height_px INT,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64) NOT NULL,     -- SHA-256 hash chống nộp lặp lại
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- [BẢNG ĐẶC THÙ NHIẾP ẢNH PHIM]
CREATE TABLE IF NOT EXISTS submission_film_metadata (
    submission_id BIGINT PRIMARY KEY REFERENCES submissions(id) ON DELETE CASCADE,
    film_stock VARCHAR(100) NOT NULL,      -- Vd: 'Kodak Portra 400', 'Fuji C200', 'Ilford HP5 Plus'
    film_iso INT,                          -- Vd: 100, 200, 400, 800, 1600
    camera_body VARCHAR(100),              -- Vd: 'Leica M6', 'Canon AE-1', 'Nikon FM2', 'Olympus OM-1'
    lens VARCHAR(100),                     -- Vd: '50mm f/1.4', '35mm f/2'
    lab_name VARCHAR(150),                 -- Vd: 'LLab Studio', 'Zone5 Darkroom', 'Croplab'
    scanner_info VARCHAR(150),             -- Vd: 'Fuji Frontier SP3000', 'Noritsu HS-1800'
    development_process VARCHAR(50) DEFAULT 'C-41', -- 'C-41', 'B&W', 'E-6', 'Push +1', 'Pull -1'
    taken_at_location VARCHAR(255),        -- Địa điểm chụp ảnh
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- PHÂN HỆ 4: PHÂN CONG & CHẤM ĐIỂM GIÁM KHẢO (SCORING)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS judge_assignments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    round_id BIGINT NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'assigned', -- 'assigned', 'grading', 'completed'
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_judge_submission UNIQUE (submission_id, judge_id)
);

CREATE TABLE IF NOT EXISTS scores (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    criteria_id BIGINT NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
    score_value NUMERIC(5,2) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_judge_criteria_score UNIQUE (submission_id, judge_id, criteria_id)
);

CREATE TABLE IF NOT EXISTS score_feedbacks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    judge_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    general_comment TEXT NOT NULL, -- Nhận xét tổng quan bức ảnh phim
    is_finalized BOOLEAN NOT NULL DEFAULT FALSE, -- Giám khảo đã chốt điểm bài này
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_judge_submission_feedback UNIQUE (submission_id, judge_id)
);

-- --------------------------------------------------------
-- PHÂN HỆ 5: AI MODULE (AI-GENERATED DETECTION & TAGGING)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_flags (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL, -- 'ai_generated_image', 'duplicate_image', 'film_grain_anomaly'
    confidence_score NUMERIC(5,2) NOT NULL, -- Xác suất nghi vấn AI (0.00 - 100.00 %)
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'confirmed_violation', 'dismissed'
    reviewed_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_analysis_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    ai_flag_id BIGINT REFERENCES ai_flags(id) ON DELETE SET NULL,
    ai_model_name VARCHAR(50) NOT NULL, -- Vd: 'DeepFake-Detector-v2', 'CLIP-Similarity'
    ai_confidence_score NUMERIC(5,2),
    similarity_matched_submission_id BIGINT REFERENCES submissions(id) ON DELETE SET NULL,
    raw_details JSONB, -- Chi tiết nhận diện nhiễu hạt phim (grain), dải màu
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- [BẢNG AI TỰ ĐỘNG GÁN NHÃN KEYWORD]
CREATE TABLE IF NOT EXISTS submission_ai_tags (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL, -- Vd: 'Street', 'Portrait', 'Monochrome', 'Urban', 'Nature'
    confidence NUMERIC(5,2) DEFAULT 90.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_submission_tag UNIQUE (submission_id, tag_name)
);

-- --------------------------------------------------------
-- PHÂN HỆ 6: TRIỂN LÃM TRỰC TUYẾN & ARCHIVE (DIGITAL ARCHIVE)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS digital_archive_exhibits (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    award_title VARCHAR(100), -- Vd: "Giải Nhất - Best Film Photo", "Giải Màu Phim Đẹp Nhất"
    display_order INT DEFAULT 0,
    views_count INT DEFAULT 0,
    likes_count INT DEFAULT 0,
    published_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_exhibit_submission UNIQUE (contest_id, submission_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'RESOLVE_AI_FLAG', 'FINALIZE_ROUND_SCORES', 'PUBLISH_EXHIBITION'
    entity_name VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES HỖ TRỢ TRUY VẤN CỰC NHANH
CREATE INDEX IF NOT EXISTS idx_film_metadata_stock ON submission_film_metadata(film_stock);
CREATE INDEX IF NOT EXISTS idx_film_metadata_camera ON submission_film_metadata(camera_body);
CREATE INDEX IF NOT EXISTS idx_submissions_round_user ON submissions(round_id, user_id);
CREATE INDEX IF NOT EXISTS idx_ai_flags_submission ON ai_flags(submission_id);
CREATE INDEX IF NOT EXISTS idx_submission_ai_tags_tag ON submission_ai_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_archive_exhibits_contest ON digital_archive_exhibits(contest_id);
