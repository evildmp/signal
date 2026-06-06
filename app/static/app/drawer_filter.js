(function () {
  const form = document.getElementById('drawer-filter-form');
  if (!form) return;
  const actionInput = form.querySelector('input[name="action"]');
  const tokenHost = form.querySelector('#drawer-ownership-tokens');

  function syncAllOwnershipTokenInputs() {
    if (!tokenHost) return;
    tokenHost.innerHTML = '';

    const tokens = DotTokens.all();

    Object.keys(tokens).forEach(function (dotId) {
      const token = tokens[dotId];
      if (!token) return;
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'ownership_token';
      input.value = token;
      tokenHost.appendChild(input);
    });
  }

  syncAllOwnershipTokenInputs();

  // Use capture phase so ownership-token inputs exist before HTMX serialises.
  form.addEventListener('change', function (e) {
    if (actionInput) {
      if (e.target && e.target.name === 'enabled') {
        actionInput.value = 'set_my_dots_only';
      } else if (e.target && e.target.name === 'team_ids') {
        actionInput.value = 'set_team_filters';
      }
    }
    syncAllOwnershipTokenInputs();
  }, true);
})();
