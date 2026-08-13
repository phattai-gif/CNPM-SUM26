# Phân Tích Yêu Cầu: Implement Màn Hình Nộp Bài cho Participant

## 1. Tổng Quan

### Mục Tiêu
Participant có thể nộp bài (hình ảnh phim) từ giao diện web với các thông tin metadata liên quan.

### Phạm Vi
- Form upload ảnh
- Form nhập metadata ảnh phim
- Gọi API nộp bài
- Hiển thị kết quả AI detection & duplicate detection

---

## 2. Phân Tích Hiện Tại

### 2.1 Backend API Hiện Có

#### Endpoint: `POST /submissions`
**Yêu cầu Authentication:** Có (JWT Token)

**Request Body:**
```json
{
  "round_id": 1,
  "title": "Tên bài nộp",
  "image_hd_url": "path/to/image.jpg",
  
  // Optional
  "story_description": "Mô tả câu chuyện",
  "thumbnail_url": "path/to/thumbnail.jpg",
  "width_px": 2000,
  "height_px": 1500,
  "file_size_bytes": 1024000,
  "file_hash": "abc123...",
  "status": "submitted",
  "comparison_image_url": "path/for/duplicate/check",
  
  // Film Metadata
  "film_metadata": {
    "film_stock": "Kodak Portra 400",
    "film_iso": 400,
    "camera_body": "Canon EOS 5D",
    "lens": "50mm f/1.8",
    "lab_name": "Tên phòng lab",
    "scanner_info": "Epson V550",
    "development_process": "C-41",
    "taken_at_location": "Thành phố A"
  }
}
```

**Response (201 - Created):**
```json
{
  "message": "Submission created successfully",
  "submission": {
    "id": 1,
    "round_id": 1,
    "user_id": 123,
    "title": "Tên bài nộp",
    "story_description": "Mô tả",
    "status": "submitted",
    "submitted_at": "2024-01-15T10:30:00"
  },
  "ai_warning": {
    "ai_score": 0,
    "ai_message": "Verified real capture device: Canon EOS 5D..."
  },
  "duplicate_warning": {
    "is_duplicate": false,
    "similarity_score": 0.15
  }
}
```

**Error Responses:**
- `400` - Missing required fields (round_id, title, image_hd_url)
- `401` - User information missing or invalid token
- `500` - Database error

### 2.2 Required Fields (Bắt Buộc)
1. **round_id** - ID của cuộc thi đang diễn ra
2. **title** - Tiêu đề/tên bài nộp
3. **image_hd_url** - Đường dẫn/URL của ảnh

### 2.3 Optional Fields (Tuỳ Chọn)
1. **story_description** - Mô tả câu chuyện đằng sau bức ảnh
2. **thumbnail_url** - URL ảnh thumbnail
3. **width_px, height_px** - Kích thước ảnh (px)
4. **file_size_bytes** - Kích thước file
5. **file_hash** - Hash của file (để check trùng lặp)
6. **Film Metadata:**
   - film_stock: Loại film sử dụng
   - film_iso: ISO của film
   - camera_body: Model máy ảnh
   - lens: Ống kính sử dụng
   - lab_name: Tên lab tẩm rửa
   - scanner_info: Thông tin máy scan
   - development_process: Quy trình tẩm rửa (mặc định: C-41)
   - taken_at_location: Địa điểm chụp

### 2.4 Tính Năng Phía Backend
- ✅ **AI Detection**: Kiểm tra ảnh có phải AI-generated không
- ✅ **Duplicate Detection**: Kiểm tra ảnh có trùng lặp với bài khác không
- ✅ **EXIF Data Extraction**: Đọc dữ liệu EXIF từ ảnh
- ✅ **Validation**: Kiểm tra các field bắt buộc

---

## 3. Kiến Trúc Form Cần Triển Khai

### 3.1 Form Nộp Bài (Submission Form)

```
┌─────────────────────────────────────────┐
│     PARTICIPANT SUBMISSION SCREEN       │
├─────────────────────────────────────────┤
│                                         │
│  SECTION 1: BASIC INFORMATION          │
│  ┌───────────────────────────────────┐ │
│  │ Round Selection: [Dropdown Menu]  │ │
│  │ (Lấy danh sách cuộc thi từ API)   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  SECTION 2: IMAGE UPLOAD              │
│  ┌───────────────────────────────────┐ │
│  │ [Image Preview Area]              │ │
│  │ - Drag & Drop                     │ │
│  │ - Click to browse                 │ │
│  │ - File Info: Size, Dimension      │ │
│  └───────────────────────────────────┘ │
│                                         │
│  SECTION 3: SUBMISSION DETAILS        │
│  ┌───────────────────────────────────┐ │
│  │ Title: [___________________]       │ │
│  │ Story Description:                │ │
│  │ [                               ] │ │
│  │ [                               ] │ │
│  └───────────────────────────────────┘ │
│                                         │
│  SECTION 4: FILM METADATA             │
│  ┌───────────────────────────────────┐ │
│  │ Camera Body: [___________________] │ │
│  │ Lens: [___________________________] │ │
│  │ Film Stock: [_____________________] │ │
│  │ Film ISO: [___] [Scale slider]   │ │
│  │ Lab Name: [___________________]   │ │
│  │ Scanner Info: [_________________] │ │
│  │ Development Process: [Dropdown]  │ │
│  │ Taken at Location: [_____________] │ │
│  └───────────────────────────────────┘ │
│                                         │
│  SECTION 5: VERIFICATION              │
│  ┌───────────────────────────────────┐ │
│  │ ⚠️  AI Detection Score: [____]     │ │
│  │ 🔍 Duplicate Check: [____]        │ │
│  │ ℹ️  Status: [Loading/Ready]        │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [Cancel Button]  [Submit Button]     │
│                                         │
└─────────────────────────────────────────┘
```

### 3.2 Form Components Chi Tiết

#### A. Round Selection (Dropdown)
- **Type:** Select field
- **Source:** GET /contests/rounds (cần tạo endpoint nếu chưa có)
- **Display:** Round name + deadline
- **Required:** Yes

#### B. Image Upload
- **Type:** File input + Drag & Drop
- **Accept:** .jpg, .jpeg, .png, .tiff, .bmp
- **Max Size:** Cần định nghĩa (recommend: 20MB)
- **Preview:** Hiển thị thumbnail + EXIF data
- **Validation:**
  - File must exist
  - Valid image format
  - File size limit
  - Extract EXIF metadata

#### C. Title Input
- **Type:** Text input
- **Length:** Max 200 characters
- **Required:** Yes
- **Validation:** Non-empty

#### D. Story Description
- **Type:** Textarea
- **Length:** Max 1000 characters
- **Required:** No
- **Placeholder:** "Tell the story behind this photograph..."

#### E. Film Metadata Form
| Field | Type | Required | Example |
|-------|------|----------|---------|
| Camera Body | Text | No | Canon EOS 5D Mark IV |
| Lens | Text | No | 50mm f/1.8 |
| Film Stock | Text | No | Kodak Portra 400 |
| Film ISO | Number | No | 400 |
| Lab Name | Text | No | Tên phòng lab |
| Scanner Info | Text | No | Epson Perfection V550 |
| Development Process | Select | No | C-41, B&W, E-6 |
| Taken at Location | Text | No | Thành phố A |

---

## 4. Luồng Xử Lý (Workflow)

```
START
  │
  ├─ User chọn cuộc thi (round_id)
  │
  ├─ User upload ảnh
  │   ├─ Validate file
  │   ├─ Extract EXIF data
  │   ├─ Calculate file hash
  │   ├─ Generate thumbnail
  │   └─ Display preview
  │
  ├─ User nhập metadata
  │   ├─ Title (bắt buộc)
  │   ├─ Story description (tuỳ chọn)
  │   ├─ Film metadata (tuỳ chọn)
  │   └─ Auto-fill EXIF data nếu có
  │
  ├─ User click "Submit"
  │   ├─ Validate form
  │   ├─ Prepare request body
  │   ├─ Call POST /submissions
  │   │   ├─ AI Detection check
  │   │   ├─ Duplicate detection check
  │   │   └─ Save to database
  │   │
  │   ├─ Handle response
  │   │   ├─ Show submission ID
  │   │   ├─ Display AI score warning
  │   │   ├─ Display duplicate warning
  │   │   └─ Redirect to submission detail page
  │   │
  │   └─ Handle error
  │       ├─ Network error
  │       ├─ Validation error
  │       └─ Server error
  │
END
```

---

## 5. Công Nghệ & Dependencies

### Frontend Stack
**Recommended:**
- **HTML5** - Form structure
- **CSS3** - Styling + Drag & Drop UI
- **Vanilla JavaScript** OR **jQuery**
- **FileReader API** - File handling
- **FormData API** - File upload
- **Fetch API** - API calls
- **EXIF.js** (optional) - Extract EXIF metadata client-side

**Alternative (Modern):**
- **React** - UI framework
- **Axios** - HTTP client
- **React Hook Form** - Form management
- **React Dropzone** - File upload

### Backend APIs Cần
1. ✅ `POST /submissions` - Create submission (CÓ)
2. ⚠️ `GET /contests/rounds` - Get active rounds (CẦN KIỂM TRA)
3. ⚠️ `GET /submissions/<id>` - Get submission details (CÓ)

---

## 6. Yêu Cầu Chi Tiết (Development Checklist)

### 6.1 Frontend Implementation
- [ ] **Create `submission.html`** - Template for submission form
  - [ ] Section 1: Round selection (dropdown)
  - [ ] Section 2: Image upload (drag & drop + file input)
  - [ ] Section 3: Submission details (title, description)
  - [ ] Section 4: Film metadata form
  - [ ] Section 5: Verification status display
  - [ ] Submit & Cancel buttons

- [ ] **Create `submission.js`** - JavaScript logic
  - [ ] Form validation logic
  - [ ] File upload handling (drag & drop)
  - [ ] Image preview & EXIF extraction
  - [ ] API call to POST /submissions
  - [ ] Error handling & user feedback
  - [ ] Loading states & success message
  - [ ] Redirect after successful submission

- [ ] **Create `submission.css`** - Styling
  - [ ] Responsive design
  - [ ] Drag & drop styling
  - [ ] Form field styling
  - [ ] Image preview styling
  - [ ] Status badge styling (AI score, duplicate warning)
  - [ ] Mobile-friendly layout

### 6.2 Backend Enhancements (If Needed)
- [ ] Verify `POST /submissions` endpoint fully working
- [ ] Check/Create `GET /contests/rounds` endpoint
- [ ] Add file upload handling (if storing files on server)
- [ ] Add EXIF data auto-extraction (already exists in `AiDetectionService`)
- [ ] Add file hash calculation
- [ ] Add thumbnail generation

### 6.3 Database Schema (Verify)
- [ ] `submission_model.py` - Core submission table
- [ ] `submission_file_model.py` - File storage metadata
- [ ] `film_metadata_model.py` - Film metadata fields
- [ ] `submission_ai_tag_model.py` - AI detection results
- [ ] Ensure all fields from API are mapped to DB

### 6.4 Integration Tests
- [ ] Test successful submission
- [ ] Test missing required fields
- [ ] Test invalid token
- [ ] Test duplicate detection
- [ ] Test AI detection scoring
- [ ] Test file validation
- [ ] Test error handling

---

## 7. Data Flow Diagram

```
┌─────────────┐
│ Participant │
└──────┬──────┘
       │
       ├─ Open submission.html
       │
       ├─ GET /contests/rounds (fetch active rounds)
       │
       │
       ├─ Upload image file
       │   ├─ Client-side validation
       │   ├─ Read file using FileReader API
       │   ├─ Extract EXIF (using exifread.js or server-side)
       │   ├─ Generate thumbnail preview
       │   └─ Display image info
       │
       ├─ Fill submission form
       │   ├─ title (required)
       │   ├─ story_description
       │   ├─ film_metadata
       │   └─ comparison_image_url (optional)
       │
       ├─ Click Submit
       │   │
       │   └─> POST /submissions
       │       ├─ Request:
       │       │   - round_id
       │       │   - title
       │       │   - image_hd_url (file path or uploaded URL)
       │       │   - story_description
       │       │   - film_metadata
       │       │   - comparison_image_url
       │       │
       │       └─ Backend Processing:
       │           ├─ Validate request
       │           ├─ Extract EXIF from image_hd_url
       │           ├─ Run AI detection (AiDetectionService)
       │           ├─ Run duplicate detection
       │           ├─ Save to database
       │           │
       │           └─ Response 201:
       │               ├─ submission (id, status, etc.)
       │               ├─ ai_warning (score, message)
       │               └─ duplicate_warning (is_duplicate, score)
       │
       └─ Display result page
           ├─ Show submission ID
           ├─ Show AI detection result
           ├─ Show duplicate warning
           └─ Offer options: View details / Submit new / Go back
```

---

## 8. Sample API Request/Response

### 8.1 Successful Request
```bash
curl -X POST http://localhost:5000/submissions \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "round_id": 1,
    "title": "My Analog Photograph",
    "image_hd_url": "/uploads/photo_2024_01_15.jpg",
    "story_description": "Captured on a sunny afternoon using expired Kodak film",
    "film_metadata": {
      "film_stock": "Kodak Gold 200",
      "film_iso": 200,
      "camera_body": "Canon AE-1",
      "lens": "50mm f/1.8",
      "lab_name": "Local Film Lab",
      "scanner_info": "Epson V550",
      "development_process": "C-41",
      "taken_at_location": "Downtown Park"
    }
  }'
```

### 8.2 Successful Response
```json
{
  "message": "Submission created successfully",
  "submission": {
    "id": 42,
    "round_id": 1,
    "user_id": 123,
    "title": "My Analog Photograph",
    "story_description": "Captured on a sunny afternoon...",
    "status": "submitted",
    "submitted_at": "2024-01-15T10:30:00"
  },
  "ai_warning": {
    "ai_score": 5,
    "ai_message": "Low AI probability. Photo appears to be authentically captured."
  },
  "duplicate_warning": {
    "is_duplicate": false,
    "similarity_score": 0.08
  }
}
```

### 8.3 Error Response (Missing Fields)
```json
{
  "message": "Missing required fields",
  "missing_fields": ["image_hd_url"],
  "status": 400
}
```

---

## 9. Tóm Tắt Công Việc

### Phase 1: Analysis ✅ (Complete)
- Analyze backend API structure
- Define form requirements
- Plan data flow

### Phase 2: Frontend Implementation (Next)
- Create HTML template
- Implement form validation
- Handle file upload
- Create JavaScript logic
- Style with CSS

### Phase 3: Integration Testing
- Test API calls
- Test error handling
- Test EXIF extraction
- Test AI detection display

### Phase 4: Deployment & Refinement
- Performance optimization
- Mobile responsiveness
- User feedback implementation

---

## 10. Estimated Effort

| Component | Effort | Duration |
|-----------|--------|----------|
| HTML Template | Low | 1-2 hours |
| JavaScript Logic | Medium | 3-4 hours |
| CSS Styling | Low | 2 hours |
| EXIF Extraction | Medium | 1-2 hours |
| API Integration | Low | 1 hour |
| Testing & QA | Medium | 2-3 hours |
| **TOTAL** | **Medium** | **10-14 hours** |

---

## 11. Referensi Tài Liệu
- Backend Controller: [src/api/controllers/submission_controller.py](../src/api/controllers/submission_controller.py)
- AI Detection Service: [src/services/ai_detection_service.py](../src/services/ai_detection_service.py)
- Role Required Decorator: [src/api/role_required.py](../src/api/role_required.py)
- Submission Model: [src/domain/models/submission.py](../src/domain/models/submission.py)
