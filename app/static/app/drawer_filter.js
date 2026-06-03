(function () {
  var form = document.getElementById('drawer-filter-form');
  if (!form) return;
  var toggle = form.querySelector('#id_enabled');
  var tokenHost = form.querySelector('#drawer-ownership-tokens');
  var teamBoxes = function () { return form.querySelectorAll('[name="team_ids"]'); };

  function syncOwnershipTokens() {
    if (!tokenHost) return;
    tokenHost.innerHTML = '';

    var tokens = {};
    try {
      tokens = JSON.parse(localStorage.getItem('dotTokens') || '{}');
    } catch (error) {
      tokens = {};
    }

    Object.keys(tokens).forEach(function (dotId) {
      var token = tokens[dotId];
      if (!token) return;
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'ownership_token';
      input.value = token;
      tokenHost.appendChild(input);
    });
  }

  syncOwnershipTokens();

  // Use capture phase so mutual-exclusion runs before HTMX serialises.
  form.addEventListener('change', function (e) {
    syncOwnershipTokens();
    if (e.target === toggle && toggle.checked) {
      teamBoxes().forEach(function (cb) { cb.checked = false; });
    } else if (e.target.name === 'team_ids' && e.target.checked) {
      if (toggle) toggle.checked = false;
    }
  }, true);
})();