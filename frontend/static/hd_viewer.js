(function () {
  function ensureArray(input) {
    if (!input) return [];
    return Array.isArray(input) ? input : [input];
  }

  function sanitizeAttachment(item, index) {
    if (!item) return null;

    if (typeof item === 'string') {
      return {
        label: 'Attachment ' + String(index + 1),
        url: item,
      };
    }

    if (typeof item === 'object') {
      const url = item.url || item.href || item.link || item.path || null;
      if (!url) return null;
      return {
        label: item.label || item.name || ('Attachment ' + String(index + 1)),
        url: url,
      };
    }

    return null;
  }

  function normalizeItems(items) {
    const defaults = [
      { key: 'main', label: 'Main Image', url: null },
      { key: 'negative', label: 'Negative Film', url: null },
      { key: 'contact', label: 'Contact Sheet', url: null },
    ];

    const source = ensureArray(items);
    const result = defaults.map(function (item) {
      const found = source.find(function (x) { return x && x.key === item.key; });
      if (!found) return item;
      return {
        key: item.key,
        label: found.label || item.label,
        url: found.url || null,
      };
    });

    const extras = source.filter(function (x) {
      return x && x.key && ['main', 'negative', 'contact'].indexOf(x.key) === -1;
    }).map(function (x) {
      return {
        key: x.key,
        label: x.label || x.key,
        url: x.url || null,
      };
    });

    return result.concat(extras);
  }

  function buildModal() {
    const modal = document.createElement('div');
    modal.className = 'hd-viewer-modal';
    modal.setAttribute('aria-hidden', 'true');

    modal.innerHTML = '' +
      '<div class="hd-viewer-card" role="dialog" aria-modal="true" aria-label="HD Image Viewer">' +
        '<div class="hd-viewer-header">' +
          '<div class="hd-viewer-title" data-role="title">HD Image Viewer</div>' +
          '<div class="hd-viewer-actions">' +
            '<button type="button" class="hd-viewer-btn" data-action="zoom-out">- Zoom</button>' +
            '<button type="button" class="hd-viewer-btn" data-action="zoom-in">+ Zoom</button>' +
            '<button type="button" class="hd-viewer-btn" data-action="reset">Reset</button>' +
            '<button type="button" class="hd-viewer-btn" data-action="close">Close</button>' +
          '</div>' +
        '</div>' +
        '<div class="hd-viewer-tabs" data-role="tabs"></div>' +
        '<div class="hd-viewer-stage" data-role="stage">' +
          '<img class="hd-viewer-image" data-role="image" alt="HD preview" draggable="false">' +
          '<div class="hd-viewer-empty" data-role="empty">Không có ảnh cho tab này.</div>' +
        '</div>' +
        '<div class="hd-viewer-footer">' +
          '<div class="hd-viewer-meta" data-role="meta">Ready</div>' +
          '<div class="hd-viewer-attachments" data-role="attachments"></div>' +
        '</div>' +
      '</div>';

    document.body.appendChild(modal);
    return modal;
  }

  function createViewer() {
    const modal = buildModal();
    const titleEl = modal.querySelector('[data-role="title"]');
    const tabsEl = modal.querySelector('[data-role="tabs"]');
    const stageEl = modal.querySelector('[data-role="stage"]');
    const imageEl = modal.querySelector('[data-role="image"]');
    const emptyEl = modal.querySelector('[data-role="empty"]');
    const metaEl = modal.querySelector('[data-role="meta"]');
    const attachmentsEl = modal.querySelector('[data-role="attachments"]');

    let items = [];
    let attachments = [];
    let activeKey = 'main';
    let zoom = 1;
    let panX = 0;
    let panY = 0;
    let pointerDown = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragStartPanX = 0;
    let dragStartPanY = 0;

    function currentItem() {
      return items.find(function (x) { return x.key === activeKey; }) || null;
    }

    function applyTransform() {
      imageEl.style.transform = 'translate(calc(-50% + ' + String(panX) + 'px), calc(-50% + ' + String(panY) + 'px)) scale(' + String(zoom) + ')';
    }

    function resetTransform() {
      zoom = 1;
      panX = 0;
      panY = 0;
      applyTransform();
      metaEl.textContent = 'Zoom: 100%';
    }

    function setImage(item) {
      if (!item || !item.url) {
        imageEl.removeAttribute('src');
        imageEl.style.display = 'none';
        emptyEl.style.display = 'flex';
        metaEl.textContent = 'Không có ảnh cho ' + (item ? item.label : 'tab này') + '.';
        return;
      }

      imageEl.src = item.url;
      imageEl.style.display = 'block';
      emptyEl.style.display = 'none';
      resetTransform();
    }

    function renderTabs() {
      tabsEl.innerHTML = '';
      items.forEach(function (item) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'hd-viewer-tab' + (item.key === activeKey ? ' active' : '');
        btn.textContent = item.label;
        btn.disabled = !item.url;
        btn.addEventListener('click', function () {
          activeKey = item.key;
          renderTabs();
          setImage(item);
        });
        tabsEl.appendChild(btn);
      });
    }

    function renderAttachments() {
      attachmentsEl.innerHTML = '';
      if (!attachments.length) {
        return;
      }

      attachments.forEach(function (item) {
        const a = document.createElement('a');
        a.className = 'hd-viewer-attachment';
        a.href = item.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = item.label;
        attachmentsEl.appendChild(a);
      });
    }

    function open(config) {
      const safeConfig = config || {};
      titleEl.textContent = safeConfig.title || 'HD Image Viewer';

      items = normalizeItems(safeConfig.items || []);
      attachments = ensureArray(safeConfig.attachments)
        .map(sanitizeAttachment)
        .filter(function (x) { return x && x.url; });

      const firstWithUrl = items.find(function (x) { return x.url; });
      activeKey = firstWithUrl ? firstWithUrl.key : 'main';

      renderTabs();
      setImage(currentItem());
      renderAttachments();

      modal.classList.add('show');
      modal.setAttribute('aria-hidden', 'false');
    }

    function close() {
      modal.classList.remove('show');
      modal.setAttribute('aria-hidden', 'true');
      pointerDown = false;
      imageEl.classList.remove('dragging');
    }

    modal.addEventListener('click', function (event) {
      if (event.target === modal) {
        close();
      }
    });

    modal.querySelector('[data-action="close"]').addEventListener('click', close);
    modal.querySelector('[data-action="zoom-in"]').addEventListener('click', function () {
      zoom = Math.min(zoom + 0.2, 5);
      applyTransform();
      metaEl.textContent = 'Zoom: ' + String(Math.round(zoom * 100)) + '%';
    });
    modal.querySelector('[data-action="zoom-out"]').addEventListener('click', function () {
      zoom = Math.max(zoom - 0.2, 0.4);
      if (zoom <= 1) {
        panX = 0;
        panY = 0;
      }
      applyTransform();
      metaEl.textContent = 'Zoom: ' + String(Math.round(zoom * 100)) + '%';
    });
    modal.querySelector('[data-action="reset"]').addEventListener('click', resetTransform);

    stageEl.addEventListener('pointerdown', function (event) {
      if (!imageEl.getAttribute('src')) return;
      pointerDown = true;
      dragStartX = event.clientX;
      dragStartY = event.clientY;
      dragStartPanX = panX;
      dragStartPanY = panY;
      imageEl.classList.add('dragging');
      try {
        stageEl.setPointerCapture(event.pointerId);
      } catch (error) {}
    });

    stageEl.addEventListener('pointermove', function (event) {
      if (!pointerDown) return;
      panX = dragStartPanX + (event.clientX - dragStartX);
      panY = dragStartPanY + (event.clientY - dragStartY);
      applyTransform();
    });

    function stopDrag(event) {
      pointerDown = false;
      imageEl.classList.remove('dragging');
      if (event) {
        try {
          stageEl.releasePointerCapture(event.pointerId);
        } catch (error) {}
      }
    }

    stageEl.addEventListener('pointerup', stopDrag);
    stageEl.addEventListener('pointercancel', stopDrag);
    stageEl.addEventListener('wheel', function (event) {
      if (!imageEl.getAttribute('src')) return;
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.12 : 0.12;
      zoom = Math.min(5, Math.max(0.4, zoom + delta));
      if (zoom <= 1) {
        panX = 0;
        panY = 0;
      }
      applyTransform();
      metaEl.textContent = 'Zoom: ' + String(Math.round(zoom * 100)) + '%';
    }, { passive: false });

    document.addEventListener('keydown', function (event) {
      if (!modal.classList.contains('show')) return;
      if (event.key === 'Escape') {
        close();
      }
    });

    return {
      open: open,
      close: close,
    };
  }

  let viewerInstance = null;

  window.HDImageViewer = {
    open: function (config) {
      if (!viewerInstance) {
        viewerInstance = createViewer();
      }
      viewerInstance.open(config || {});
    },
    close: function () {
      if (viewerInstance) {
        viewerInstance.close();
      }
    },
  };
})();
