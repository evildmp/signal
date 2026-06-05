(function () {
  const nav = document.getElementById('l-navigation');
  const menuToggle = document.getElementById('menu-toggle');
  const menuClose = document.getElementById('menu-close');
  const menuPin = document.getElementById('menu-pin');

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