(function () {
  const grid = document.getElementById('signal-grid');
  if (!grid) return;

  let lastCompletedGesture = null;
  let dragState = null;
  let gridPointerGesture = null;
  const dragSelectionClass = 'signal-dragging';

  function setDragSelectionSuppressed(isSuppressed) {
    if (isSuppressed) {
      document.body.classList.add(dragSelectionClass);
    } else {
      document.body.classList.remove(dragSelectionClass);
    }
  }

  function ownershipTokenForDot(dot, tokens) {
    const id = dot.dataset.dotId;
    return tokens[id] || '';
  }

  function updateClaimedDotClasses() {
    const tokens = DotTokens.all();
    document.querySelectorAll('.signal-dot').forEach(function (dot) {
      const isOwnedByUser = dot.dataset.ownedByUser === '1';
      const hasOwnershipToken = !!ownershipTokenForDot(dot, tokens);
      if (isOwnedByUser || hasOwnershipToken) {
        dot.classList.add('signal-dot--claimed');
      } else {
        dot.classList.remove('signal-dot--claimed');
      }
    });
  }

  function ownershipTokenForDotId(dotId) {
    return DotTokens.get(dotId);
  }

  // Initial mark — uses localStorage presence only; verification fetch below
  // corrects any stale entries without requiring the token to be in the DOM.
  updateClaimedDotClasses();

  (function verifyOwnershipTokens() {
    const tokens = DotTokens.all();
    const entries = Object.entries(tokens);
    if (entries.length === 0) return;

    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const body = new URLSearchParams();
    body.append('csrfmiddlewaretoken', csrf);
    entries.forEach(function (entry) {
      body.append('dot_token', entry[0] + ':' + entry[1]);
    });

    fetch('/verify-tokens/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf },
      body: body,
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        const verifiedIds = new Set(data.verified_dot_ids.map(String));
        entries.forEach(function (entry) {
          const dotId = entry[0];
          if (!verifiedIds.has(dotId)) {
            DotTokens.remove(dotId);
            const dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
            if (dot) dot.dataset.ownedByUser = '0';
          } else {
            const dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
            if (dot) dot.dataset.ownedByUser = '1';
          }
        });
        updateClaimedDotClasses();
      })
      .catch(function () { /* network failure — leave current state intact */ });
  }());

  // After grid redraw (e.g. filter change)
  document.body.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'signal-grid') {
      setTimeout(updateClaimedDotClasses, 0);
    }
  });

  document.body.addEventListener('htmx:configRequest', function (e) {
    if (!e.detail || !e.detail.path) return;

    const match = e.detail.path.match(/^\/dot\/(\d+)\//);
    if (!match) return;

    const token = DotTokens.get(match[1]);
    if (token) {
      e.detail.headers = e.detail.headers || {};
      e.detail.headers['X-Ownership-Token'] = token;
    }
  });

  function clampPercent(value) {
    return Math.max(0, Math.min(100, value));
  }

  function gridPercentFromPointer(clientX, clientY) {
    const rect = grid.getBoundingClientRect();
    const x = (clientX - rect.left) / rect.width * 100;
    const y = 100 - (clientY - rect.top) / rect.height * 100;
    return {
      x: clampPercent(x),
      y: clampPercent(y)
    };
  }

  function labelPositionClass(x, y) {
    const labelY = y > 50 ? 'bottom' : 'top';
    const labelX = x >= 50 ? 'left' : 'right';
    return 'signal-dot-label--' + labelY + '-' + labelX;
  }

  function labelForDotId(dotId) {
    return document.querySelector('.signal-dot-published-label[data-dot-id="' + dotId + '"]');
  }

  function applyLabelPosition(label, x, y) {
    if (!label) return;
    label.style.setProperty('--dot-x', String(x));
    label.style.setProperty('--dot-y', String(y));
    label.classList.remove(
      'signal-dot-label--top-left',
      'signal-dot-label--top-right',
      'signal-dot-label--bottom-left',
      'signal-dot-label--bottom-right'
    );
    labelPositionClass(x, y).split(' ').forEach(function (klass) {
      label.classList.add(klass);
    });
  }

  function endDrag() {
    if (!dragState) return;
    document.removeEventListener('pointermove', onDragMove);
    document.removeEventListener('pointerup', onDragEnd);
    document.removeEventListener('pointercancel', onDragEnd);

    if (dragState.hadPointerCapture && dragState.captureTarget && typeof dragState.captureTarget.releasePointerCapture === 'function') {
      try {
        dragState.captureTarget.releasePointerCapture(dragState.pointerId);
      } catch (_) {
        // Ignore release errors from synthetic or already-finished pointers.
      }
    }

    const finishedDrag = dragState;
    dragState = null;
    setDragSelectionSuppressed(false);

    if (!finishedDrag.didMove || !finishedDrag.lastPosition) return;

    const snappedPosition = {
      x: Math.round(finishedDrag.lastPosition.x),
      y: Math.round(finishedDrag.lastPosition.y)
    };

    finishedDrag.dot.style.setProperty('--dot-x', String(snappedPosition.x));
    finishedDrag.dot.style.setProperty('--dot-y', String(snappedPosition.y));
    applyLabelPosition(labelForDotId(finishedDrag.dot.dataset.dotId), snappedPosition.x, snappedPosition.y);

    lastCompletedGesture = finishedDrag;
    htmx.ajax('POST', '/dot/' + finishedDrag.dot.dataset.dotId + '/move/', {
      swap: 'none',
      values: {
        x: snappedPosition.x,
        y: snappedPosition.y
      },
      headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
    });
  }

  function onDragMove(e) {
    if (!dragState) return;
    if (e.pointerId !== dragState.pointerId) return;

    e.preventDefault();

    if (Math.abs(e.clientX - dragState.startClientX) + Math.abs(e.clientY - dragState.startClientY) > 3) {
      dragState.didMove = true;
    }

    const position = gridPercentFromPointer(e.clientX, e.clientY);
    dragState.lastPosition = position;
    dragState.dot.style.setProperty('--dot-x', position.x.toFixed(2));
    dragState.dot.style.setProperty('--dot-y', position.y.toFixed(2));
    applyLabelPosition(labelForDotId(dragState.dot.dataset.dotId), position.x, position.y);
  }

  function onDragEnd(e) {
    if (!dragState) return;
    if (e.pointerId !== dragState.pointerId) return;
    endDrag();
  }

  function onGridPointerMove(e) {
    if (!gridPointerGesture) return;
    if (e.pointerId !== gridPointerGesture.pointerId) return;

    if (Math.abs(e.clientX - gridPointerGesture.startClientX) + Math.abs(e.clientY - gridPointerGesture.startClientY) > 3) {
      gridPointerGesture.didMove = true;
    }
  }

  function onGridPointerUp(e) {
    if (!gridPointerGesture) return;
    if (e.pointerId !== gridPointerGesture.pointerId) return;

    document.removeEventListener('pointermove', onGridPointerMove);
    document.removeEventListener('pointerup', onGridPointerUp);
    document.removeEventListener('pointercancel', onGridPointerUp);

    if (gridPointerGesture.hadPointerCapture && gridPointerGesture.captureTarget && typeof gridPointerGesture.captureTarget.releasePointerCapture === 'function') {
      try {
        gridPointerGesture.captureTarget.releasePointerCapture(gridPointerGesture.pointerId);
      } catch (_) {
        // Ignore release errors from synthetic or already-finished pointers.
      }
    }

    const finishedGesture = gridPointerGesture;
    gridPointerGesture = null;

    if (finishedGesture.didMove) {
      lastCompletedGesture = finishedGesture;
    }
  }

  function beginGridPointerGesture(e) {
    const captureTarget = e.currentTarget;
    const shouldCapturePointer = e.pointerType !== 'mouse';

    gridPointerGesture = {
      didMove: false,
      pointerId: e.pointerId,
      captureTarget: captureTarget,
      hadPointerCapture: false,
      startClientX: e.clientX,
      startClientY: e.clientY
    };

    if (shouldCapturePointer && captureTarget && typeof captureTarget.setPointerCapture === 'function') {
      try {
        captureTarget.setPointerCapture(e.pointerId);
        gridPointerGesture.hadPointerCapture = true;
      } catch (_) {
        // Ignore capture errors from synthetic pointers used in tests.
      }
    }

    document.addEventListener('pointermove', onGridPointerMove);
    document.addEventListener('pointerup', onGridPointerUp);
    document.addEventListener('pointercancel', onGridPointerUp);
  }

  function clearTransientDotLabels() {
    document.querySelectorAll('.signal-dot-notification').forEach(function (label) {
      label.remove();
    });
  }

  grid.addEventListener('pointerdown', function (e) {
    if (e.button !== 0 || !e.isPrimary) return;

    clearTransientDotLabels();

    const dot = e.target.closest('.signal-dot');

    if (!dot) {
      beginGridPointerGesture(e);
      return;
    }

    const localToken = ownershipTokenForDotId(dot.dataset.dotId);
    const isOwnedByUser = dot.dataset.ownedByUser === '1';
    if (!localToken && !isOwnedByUser) {
      beginGridPointerGesture(e);
      return;
    }

    dragState = {
      dot: dot,
      didMove: false,
      pointerId: e.pointerId,
      captureTarget: dot,
      hadPointerCapture: false,
      startClientX: e.clientX,
      startClientY: e.clientY,
      lastPosition: null
    };

    setDragSelectionSuppressed(true);

    if (e.pointerType !== 'mouse' && dot && typeof dot.setPointerCapture === 'function') {
      try {
        dot.setPointerCapture(e.pointerId);
        dragState.hadPointerCapture = true;
      } catch (_) {
        // Ignore capture errors from synthetic pointers used in tests.
      }
    }

    document.addEventListener('pointermove', onDragMove);
    document.addEventListener('pointerup', onDragEnd);
    document.addEventListener('pointercancel', onDragEnd);
  });

  grid.addEventListener('click', function (e) {
    if (lastCompletedGesture && lastCompletedGesture.didMove) return;
    if (e.target.closest('.signal-dot, .signal-axis')) return;
    const position = gridPercentFromPointer(e.clientX, e.clientY);
    const x = Math.round(position.x);
    const y = Math.round(position.y);

    htmx.ajax('POST', grid.dataset.createUrl, {
      target: grid,
      swap: 'beforeend',
      values: { 'x': x, 'y': y },
      headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
    });
  });

  document.addEventListener('click', function (e) {
    if (!lastCompletedGesture || !lastCompletedGesture.didMove) return;
    if (!e.target.closest('.signal-dot')) return;
    e.preventDefault();
    e.stopPropagation();
  }, true);

  document.body.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'dot-editor-host') {
      const dialog = e.detail.target.querySelector('dialog');
      if (dialog && !dialog.open) {
        dialog.showModal();
        const focusTarget = dialog.querySelector(
          '[autofocus], input:not([type="hidden"]):not([disabled]), button:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
        );
        if (focusTarget) {
          focusTarget.focus();
        } else {
          dialog.focus();
        }
      }
    }
  });

  document.body.addEventListener('dotClaimed', function (e) {
    if (e.detail) {
      DotTokens.set(String(e.detail.dotId), e.detail.token);
      const dot = document.querySelector('.signal-dot[data-dot-id="' + e.detail.dotId + '"]');
      if (dot) {
        dot.dataset.ownedByUser = '1';
      }
      setTimeout(updateClaimedDotClasses, 0);
    }
  });

  document.body.addEventListener('dotDeleted', function (e) {
    if (!e.detail || !e.detail.dotId) return;
    DotTokens.remove(String(e.detail.dotId));
  });

  document.body.addEventListener('dotUpdated', function (e) {
    if (!e.detail || !e.detail.dotId) return;

    const dotId = String(e.detail.dotId);
    const dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
    if (!dot) return;

    dot.dataset.ownedByUser = e.detail.ownedByUser ? '1' : '0';
    updateClaimedDotClasses();

    if (e.detail.notificationHtml && grid) {
      clearTransientDotLabels();
      const container = document.createElement('div');
      container.innerHTML = e.detail.notificationHtml.trim();
      const transientLabel = container.firstElementChild;
      if (transientLabel) {
        grid.appendChild(transientLabel);
      }
    }

    const existing = labelForDotId(dotId);
    if (existing) {
      existing.remove();
    }

    if (!e.detail.publishedLabelHtml) return;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = e.detail.publishedLabelHtml.trim();
    const label = wrapper.firstElementChild;
    if (label) {
      dot.insertAdjacentElement('afterend', label);
    }
  });
})();