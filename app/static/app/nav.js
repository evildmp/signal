(function () {
  var nav = document.getElementById('l-navigation');
  var menuToggle = document.getElementById('menu-toggle');
  var menuClose = document.getElementById('menu-close');
  var menuPin = document.getElementById('menu-pin');

  if (menuToggle) {
    menuToggle.addEventListener('click', function () {
      nav.classList.toggle('is-collapsed');
    });
  }

  if (menuClose) {
    menuClose.addEventListener('click', function () {
      nav.classList.add('is-collapsed');
    });
  }

  if (menuPin) {
    menuPin.addEventListener('click', function () {
      nav.classList.toggle('is-pinned');
    });
  }
})();