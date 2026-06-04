(function () {
  var grid = document.getElementById('signal-grid');
  if (!grid) return;

  var suppressNextGridClick = false;
  var dragState = null;
  var gridPointerGesture = null;

  function suppressGridClickAfterPointerUp() {
    suppressNextGridClick = true;
    setTimeout(function () {
      suppressNextGridClick = false;
    }, 0);
  }

  function thresholdFromData(attributeName, fallback) {
    var raw = grid.dataset[attributeName];
    var parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  var labelLeftEdgeThreshold = thresholdFromData('labelLeftEdgeThreshold', 20);
  var labelRightEdgeThreshold = thresholdFromData('labelRightEdgeThreshold', 80);
  var labelTopEdgeThreshold = thresholdFromData('labelTopEdgeThreshold', 80);

  function ownershipTokenForDot(dot, tokens) {
    var id = dot.dataset.dotId;
    return tokens[id] || '';
  }

  function updateClaimedDotClasses() {
    var tokens = JSON.parse(localStorage.getItem('dotTokens') || '{}');
    document.querySelectorAll('.signal-dot').forEach(function (dot) {
      var isOwnedByUser = dot.dataset.ownedByUser === '1';
      var hasOwnershipToken = !!ownershipTokenForDot(dot, tokens);
      if (isOwnedByUser || hasOwnershipToken) {
        dot.classList.add('signal-dot--claimed');
      } else {
        dot.classList.remove('signal-dot--claimed');
      }
    });
  }

  function ownershipTokenForDotId(dotId) {
    var dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
    if (!dot) return '';
    var tokens = JSON.parse(localStorage.getItem('dotTokens') || '{}');
    return ownershipTokenForDot(dot, tokens);
  }

  // Initial mark
  updateClaimedDotClasses();

  // After new dot claim
  document.body.addEventListener('dotClaimed', function () {
    setTimeout(updateClaimedDotClasses, 0);
  });

  // After grid redraw (e.g. filter change)
  document.body.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'signal-grid') {
      setTimeout(updateClaimedDotClasses, 0);
    }
  });

  document.body.addEventListener('htmx:configRequest', function (e) {
    if (!e.detail || !e.detail.path || e.detail.verb !== 'get') return;

    var match = e.detail.path.match(/^\/dot\/(\d+)\/edit\/$/);
    if (!match) return;

    var dotId = match[1];
    var token = ownershipTokenForDotId(dotId);
    if (token) {
      e.detail.headers = e.detail.headers || {};
      e.detail.headers['X-Ownership-Token'] = token;
    }
  });

  function clampPercent(value) {
    return Math.max(0, Math.min(100, value));
  }

  function gridPercentFromPointer(clientX, clientY) {
    var rect = grid.getBoundingClientRect();
    var x = (clientX - rect.left) / rect.width * 100;
    var y = 100 - (clientY - rect.top) / rect.height * 100;
    return {
      x: clampPercent(x),
      y: clampPercent(y)
    };
  }

  function labelPositionClass(x, y) {
    var labelY = y > labelTopEdgeThreshold ? 'below' : 'above';
    var labelX = 'center';
    if (x < labelLeftEdgeThreshold) {
      labelX = 'right';
    } else if (x > labelRightEdgeThreshold) {
      labelX = 'left';
    }

    if (labelX !== 'center') {
      labelY = 'side';
    }

    return 'signal-dot-label--' + labelY + ' signal-dot-label--x-' + labelX;
  }

  function labelForDotId(dotId) {
    return document.querySelector('.signal-dot-published-label[data-dot-id="' + dotId + '"]');
  }

  function applyLabelPosition(label, x, y) {
    if (!label) return;
    label.style.setProperty('--dot-x', String(x));
    label.style.setProperty('--dot-y', String(y));
    label.classList.remove(
      'signal-dot-label--above',
      'signal-dot-label--below',
      'signal-dot-label--side',
      'signal-dot-label--x-left',
      'signal-dot-label--x-right',
      'signal-dot-label--x-center'
    );
    labelPositionClass(x, y).split(' ').forEach(function (klass) {
      label.classList.add(klass);
    });
  }

  function endDrag() {
    if (!dragState) return;
    document.removeEventListener('mousemove', onDragMove);
    document.removeEventListener('mouseup', onDragEnd);

    var finishedDrag = dragState;
    dragState = null;

    if (!finishedDrag.didMove || !finishedDrag.lastPosition) return;

    var snappedPosition = {
      x: Math.round(finishedDrag.lastPosition.x),
      y: Math.round(finishedDrag.lastPosition.y)
    };

    finishedDrag.dot.style.setProperty('--dot-x', String(snappedPosition.x));
    finishedDrag.dot.style.setProperty('--dot-y', String(snappedPosition.y));
    applyLabelPosition(labelForDotId(finishedDrag.dot.dataset.dotId), snappedPosition.x, snappedPosition.y);

    var ownershipToken = finishedDrag.ownershipToken || '';

    suppressGridClickAfterPointerUp();
    htmx.ajax('POST', '/dot/' + finishedDrag.dot.dataset.dotId + '/move/', {
      swap: 'none',
      values: {
        x: snappedPosition.x,
        y: snappedPosition.y,
        ownership_token: ownershipToken
      },
      headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
    });
  }

  function onDragMove(e) {
    if (!dragState) return;

    if (Math.abs(e.clientX - dragState.startClientX) + Math.abs(e.clientY - dragState.startClientY) > 3) {
      dragState.didMove = true;
    }

    var position = gridPercentFromPointer(e.clientX, e.clientY);
    dragState.lastPosition = position;
    dragState.dot.style.setProperty('--dot-x', position.x.toFixed(2));
    dragState.dot.style.setProperty('--dot-y', position.y.toFixed(2));
    applyLabelPosition(labelForDotId(dragState.dot.dataset.dotId), position.x, position.y);
  }

  function onDragEnd() {
    endDrag();
  }

  function onGridPointerMove(e) {
    if (!gridPointerGesture) return;

    if (Math.abs(e.clientX - gridPointerGesture.startClientX) + Math.abs(e.clientY - gridPointerGesture.startClientY) > 3) {
      gridPointerGesture.didMove = true;
    }
  }

  function onGridPointerUp() {
    if (!gridPointerGesture) return;

    document.removeEventListener('mousemove', onGridPointerMove);
    document.removeEventListener('mouseup', onGridPointerUp);

    var finishedGesture = gridPointerGesture;
    gridPointerGesture = null;

    if (finishedGesture.didMove) {
      suppressGridClickAfterPointerUp();
    }
  }

  function beginGridPointerGesture(e) {
    gridPointerGesture = {
      didMove: false,
      startClientX: e.clientX,
      startClientY: e.clientY
    };

    document.addEventListener('mousemove', onGridPointerMove);
    document.addEventListener('mouseup', onGridPointerUp);
  }

  function clearTransientDotLabels() {
    document.querySelectorAll('.signal-dot-label').forEach(function (label) {
      label.remove();
    });
  }

  grid.addEventListener('mousedown', function (e) {
    clearTransientDotLabels();

    var dot = e.target.closest('.signal-dot');

    if (!dot) {
      beginGridPointerGesture(e);
      return;
    }

    var ownershipToken = ownershipTokenForDotId(dot.dataset.dotId);
    var isOwnedByUser = dot.dataset.ownedByUser === '1';
    if (!ownershipToken && !isOwnedByUser) {
      beginGridPointerGesture(e);
      return;
    }

    dragState = {
      dot: dot,
      didMove: false,
      startClientX: e.clientX,
      startClientY: e.clientY,
      lastPosition: null,
      ownershipToken: ownershipToken
    };

    document.addEventListener('mousemove', onDragMove);
    document.addEventListener('mouseup', onDragEnd);
    e.preventDefault();
  });

  grid.addEventListener('click', function (e) {
    if (suppressNextGridClick) return;
    if (e.target.closest('.signal-dot, .signal-axis')) return;
    var position = gridPercentFromPointer(e.clientX, e.clientY);
    var x = Math.round(position.x);
    var y = Math.round(position.y);

    htmx.ajax('POST', grid.dataset.createUrl, {
      target: grid,
      swap: 'beforeend',
      values: { 'x': x, 'y': y },
      headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
    });
  });

  document.addEventListener('click', function (e) {
    if (!suppressNextGridClick) return;
    if (!e.target.closest('.signal-dot')) return;
    e.preventDefault();
    e.stopPropagation();
  }, true);

  document.body.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'dot-editor-host') {
      var dialog = e.detail.target.querySelector('dialog');
      if (dialog && !dialog.open) {
        dialog.showModal();
        var focusTarget = dialog.querySelector(
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
      var tokens = JSON.parse(localStorage.getItem('dotTokens') || '{}');
      tokens[String(e.detail.dotId)] = e.detail.token;
      localStorage.setItem('dotTokens', JSON.stringify(tokens));
      var dot = document.querySelector('.signal-dot[data-dot-id="' + e.detail.dotId + '"]');
      if (dot) {
        dot.dataset.ownedByUser = '1';
      }
    }
  });

  document.body.addEventListener('dotDeleted', function (e) {
    if (!e.detail || !e.detail.dotId) return;

    var dotId = String(e.detail.dotId);
    var dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
    if (dot) {
      dot.remove();
    }

    var label = labelForDotId(dotId);
    if (label) {
      label.remove();
    }

    var tokens = JSON.parse(localStorage.getItem('dotTokens') || '{}');
    if (tokens[dotId]) {
      delete tokens[dotId];
      localStorage.setItem('dotTokens', JSON.stringify(tokens));
    }
  });

  document.body.addEventListener('dotUpdated', function (e) {
    if (!e.detail || !e.detail.dotId) return;

    var dotId = String(e.detail.dotId);
    var dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
    if (!dot) return;

    dot.dataset.ownedByUser = e.detail.ownedByUser ? '1' : '0';
    updateClaimedDotClasses();

    if (e.detail.notificationHtml && grid) {
      clearTransientDotLabels();
      var container = document.createElement('div');
      container.innerHTML = e.detail.notificationHtml.trim();
      var transientLabel = container.firstElementChild;
      if (transientLabel) {
        grid.appendChild(transientLabel);
      }
    }

    var existing = labelForDotId(dotId);
    if (existing) {
      existing.remove();
    }

    if (!e.detail.publishedLabelHtml) return;

    var wrapper = document.createElement('div');
    wrapper.innerHTML = e.detail.publishedLabelHtml.trim();
    var label = wrapper.firstElementChild;
    if (label) {
      dot.insertAdjacentElement('afterend', label);
    }
  });
})();