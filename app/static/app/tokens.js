var DotTokens = (function () {
  var KEY = 'dotTokens';

  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || '{}');
    } catch (e) {
      return {};
    }
  }

  function save(tokens) {
    localStorage.setItem(KEY, JSON.stringify(tokens));
  }

  return {
    all: function () {
      return load();
    },
    get: function (id) {
      return load()[String(id)] || '';
    },
    set: function (id, token) {
      var tokens = load();
      tokens[String(id)] = token;
      save(tokens);
    },
    remove: function (id) {
      var tokens = load();
      delete tokens[String(id)];
      save(tokens);
    }
  };
})();
