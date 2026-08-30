/**
 * Gallery JS - FE06.1 & FE06.2 Implementation
 * Handles public gallery layout, filter controls, pagination & photo modal preview.
 */

let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let submissionsData = [];
let searchTimeout = null;
let activeModalSubmissionId = null;

document.addEventListener('DOMContentLoaded', () => {
  initGalleryFilters();
  loadGallery(1);
});

/**
 * Fetch available filter metadata (film stocks, cameras, contests, years)
 */
async function initGalleryFilters() {
  try {
    const resp = await fetch('/api/gallery/filters');
    if (!resp.ok) return;

    const data = await resp.json();

    // Film stocks
    const filmStockSelect = document.getElementById('filterFilmStock');
    if (filmStockSelect && data.film_stocks) {
      data.film_stocks.forEach(stock => {
        const opt = document.createElement('option');
        opt.value = stock;
        opt.textContent = stock;
        filmStockSelect.appendChild(opt);
      });
    }

    // Cameras
    const cameraSelect = document.getElementById('filterCamera');
    if (cameraSelect && data.cameras) {
      data.cameras.forEach(cam => {
        const opt = document.createElement('option');
        opt.value = cam;
        opt.textContent = cam;
        cameraSelect.appendChild(opt);
      });
    }

    // Contests
    const contestSelect = document.getElementById('filterContest');
    if (contestSelect && data.contests) {
      data.contests.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.title;
        contestSelect.appendChild(opt);
      });
    }

    // Years
    const yearSelect = document.getElementById('filterYear');
    if (yearSelect && data.years) {
      data.years.forEach(y => {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = `Năm ${y}`;
        yearSelect.appendChild(opt);
      });
    }
  } catch (error) {
    console.error('Error loading gallery filter metadata:', error);
  }
}

/**
 * Load public gallery submissions with filters and pagination
 */
async function loadGallery(page = 1) {
  currentPage = page;

  const loadingEl = document.getElementById('galleryLoading');
  const gridEl = document.getElementById('galleryGrid');
  const emptyEl = document.getElementById('galleryEmpty');
  const paginationEl = document.getElementById('galleryPagination');

  loadingEl.style.display = 'block';
  gridEl.style.display = 'none';
  emptyEl.style.display = 'none';
  paginationEl.style.display = 'none';

  // Read current filters
  const filmStock = document.getElementById('filterFilmStock')?.value || '';
  const camera = document.getElementById('filterCamera')?.value || '';
  const contestId = document.getElementById('filterContest')?.value || '';
  const year = document.getElementById('filterYear')?.value || '';
  const search = document.getElementById('filterSearch')?.value || '';

  // Build query string
  const params = new URLSearchParams();
  params.append('page', page);
  params.append('limit', 12);
  if (filmStock) params.append('film_stock', filmStock);
  if (camera) params.append('camera', camera);
  if (contestId) params.append('contest_id', contestId);
  if (year) params.append('year', year);
  if (search) params.append('search', search);

  try {
    const resp = await fetch(`/api/gallery?${params.toString()}`);
    if (!resp.ok) {
      throw new Error(`API error: ${resp.status}`);
    }

    const data = await resp.json();
    submissionsData = data.submissions || [];
    totalCount = data.total || 0;
    totalPages = data.total_pages || 1;

    loadingEl.style.display = 'none';

    if (submissionsData.length === 0) {
      emptyEl.style.display = 'block';
      updateFilterSummary(0, filmStock, camera, contestId, year, search);
      return;
    }

    renderGalleryGrid(submissionsData);
    renderPagination(page, totalPages, totalCount);
    updateFilterSummary(totalCount, filmStock, camera, contestId, year, search);

    gridEl.style.display = 'grid';
    paginationEl.style.display = 'flex';

  } catch (error) {
    console.error('Error loading gallery:', error);
    loadingEl.style.display = 'none';
    emptyEl.style.display = 'block';
  }
}

/**
 * Render grid cards
 */
function renderGalleryGrid(items) {
  const gridEl = document.getElementById('galleryGrid');
  gridEl.innerHTML = '';

  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'gallery-card';
    card.onclick = () => openPhotoDetailModal(item.id);

    const thumbnailSrc = item.thumbnail_url || item.image_hd_url || '/static/images/placeholder.jpg';
    const filmBadge = item.film_metadata?.film_stock ? `<span class="badge-film">${escapeHtml(item.film_metadata.film_stock)}</span>` : '';
    const cameraBadge = item.film_metadata?.camera_body ? `<span class="badge-camera">${escapeHtml(item.film_metadata.camera_body)}</span>` : '';
    const contestTitle = item.contest?.title ? escapeHtml(item.contest.title) : 'Cuộc thi ảnh';
    const authorName = item.author?.name ? escapeHtml(item.author.name) : 'Tác giả';
    const authorAvatar = item.author?.avatar_url || 'https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(authorName);

    card.innerHTML = `
      <div class="card-img-wrap">
        <img src="${thumbnailSrc}" alt="${escapeHtml(item.title)}" loading="lazy" onerror="this.src='/static/images/placeholder.jpg'"
        <div class="card-overlay">
          ${filmBadge}
          ${cameraBadge}
        </div>
      </div>
      <div class="gallery-card-body">
        <div>
          <div class="card-contest-name">
            <i class="bi bi-trophy-fill"></i> ${contestTitle}
          </div>
          <h5 class="card-photo-title">${escapeHtml(item.title || 'Chưa có tiêu đề')}</h5>
        </div>
        <div class="card-meta-footer">
          <div class="author-info">
            <img src="${authorAvatar}" class="author-avatar" alt="${authorName}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=user'">
            <span class="author-name">${authorName}</span>
          </div>
          <div>
            ${item.year ? `<i class="bi bi-calendar3 me-1"></i>${item.year}` : ''}
          </div>
        </div>
      </div>
    `;

    gridEl.appendChild(card);
  });
}

/**
 * Render pagination controls
 */
function renderPagination(current, total, count) {
  const container = document.getElementById('galleryPagination');
  container.innerHTML = '';

  if (total <= 1) return;

  // Previous button
  const prevBtn = document.createElement('button');
  prevBtn.className = 'page-btn';
  prevBtn.disabled = current <= 1;
  prevBtn.innerHTML = '<i class="bi bi-chevron-left"></i> Truớc';
  prevBtn.onclick = () => loadGallery(current - 1);
  container.appendChild(prevBtn);

  // Page Numbers
  let startPage = Math.max(1, current - 2);
  let endPage = Math.min(total, startPage + 4);

  if (endPage - startPage < 4) {
    startPage = Math.max(1, endPage - 4);
  }

  for (let p = startPage; p <= endPage; p++) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${p === current ? 'active' : ''}`;
    btn.textContent = p;
    btn.onclick = () => loadGallery(p);
    container.appendChild(btn);
  }

  // Next button
  const nextBtn = document.createElement('button');
  nextBtn.className = 'page-btn';
  nextBtn.disabled = current >= total;
  nextBtn.innerHTML = 'Sau <i class="bi bi-chevron-right"></i>';
  nextBtn.onclick = () => loadGallery(current + 1);
  container.appendChild(nextBtn);
}

/**
 * Open detail modal for a specific submission ID
 */
function openPhotoDetailModal(submissionId) {
  const item = submissionsData.find(s => s.id === submissionId);
  activeModalSubmissionId = submissionId;

  if (item) {
    populateModalData(item);
    const modal = new bootstrap.Modal(document.getElementById('photoDetailModal'));
    modal.show();
  } else {
    // Fetch directly if not present in memory
    fetch(`/api/gallery/${submissionId}`)
      .then(res => res.json())
      .then(data => {
        if (data.submission) {
          populateModalData(data.submission);
          const modal = new bootstrap.Modal(document.getElementById('photoDetailModal'));
          modal.show();
        }
      })
      .catch(err => console.error('Error fetching photo detail:', err));
  }
}

function populateModalData(item) {
  document.getElementById('modalPhotoTitle').textContent = item.title || 'Chi tiết tác phẩm';
  document.getElementById('modalPhotoHeaderTitle').textContent = item.title || 'Không tiêu đề';
  document.getElementById('modalPhotoImg').src = item.image_hd_url || item.thumbnail_url || '';
  document.getElementById('modalContestBadge').textContent = item.contest?.title || 'Cuộc thi';
  document.getElementById('modalAuthorName').textContent = item.author?.name || 'Tác giả vô danh';
  document.getElementById('modalPhotoYear').textContent = item.year ? `Năm ${item.year}` : '';

  document.getElementById('modalStoryText').textContent = item.story_description || 'Chưa có câu chuyện đi kèm tác phẩm này.';

  const meta = item.film_metadata || {};
  document.getElementById('modalFilmStock').textContent = meta.film_stock || '-';
  document.getElementById('modalCamera').textContent = meta.camera_body || '-';
  document.getElementById('modalLens').textContent = meta.lens || '-';
  document.getElementById('modalISO').textContent = meta.film_iso || '-';
  document.getElementById('modalLab').textContent = meta.lab_name || '-';
  document.getElementById('modalLocation').textContent = meta.taken_at_location || '-';

  document.getElementById('modalDirectLink').href = `/gallery/${item.id}`;
}

/**
 * Update filter summary label
 */
function updateFilterSummary(total, filmStock, camera, contestId, year, search) {
  const summaryEl = document.getElementById('activeFiltersSummary');
  let text = `Tìm thấy <strong>${total}</strong> tác phẩm công khai`;

  const active = [];
  if (filmStock) active.push(`Film: <i>${escapeHtml(filmStock)}</i>`);
  if (camera) active.push(`Máy: <i>${escapeHtml(camera)}</i>`);
  if (contestId) active.push(`Cuộc thi ID: <i>${escapeHtml(contestId)}</i>`);
  if (year) active.push(`Năm: <i>${escapeHtml(year)}</i>`);
  if (search) active.push(`Từ khóa: "<i>${escapeHtml(search)}</i>"`);

  if (active.length > 0) {
    text += ` với bộ lọc [ ${active.join(' • ')} ]`;
  }
  summaryEl.innerHTML = text;
}

/**
 * Filter triggers
 */
function applyFilters() {
  loadGallery(1);
}

function resetFilters() {
  if (document.getElementById('filterFilmStock')) document.getElementById('filterFilmStock').value = '';
  if (document.getElementById('filterCamera')) document.getElementById('filterCamera').value = '';
  if (document.getElementById('filterContest')) document.getElementById('filterContest').value = '';
  if (document.getElementById('filterYear')) document.getElementById('filterYear').value = '';
  if (document.getElementById('filterSearch')) document.getElementById('filterSearch').value = '';

  loadGallery(1);
}

function debounceSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    applyFilters();
  }, 400);
}

function copyPhotoLink() {
  if (activeModalSubmissionId) {
    const fullUrl = `${window.location.origin}/gallery/${activeModalSubmissionId}`;
    navigator.clipboard.writeText(fullUrl);
    alert('Đã sao chép liên kết tác phẩm vào bộ nhớ tạm!');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
ss