(function () {
  const onboardingDialog = document.getElementById('signal-onboarding-dialog');
  const onboardingOpen = document.getElementById('signal-onboarding-open');

  if (!onboardingDialog) return;

  if (onboardingDialog.dataset.showOnLoad === '1' && !onboardingDialog.open) {
    onboardingDialog.showModal();
  }

  if (onboardingOpen) {
    onboardingOpen.addEventListener('click', function (e) {
      e.preventDefault();
      if (!onboardingDialog.open) {
        onboardingDialog.showModal();
      }
    });
  }

  const dismissForm = document.getElementById('signal-onboarding-dismiss-form');
  if (dismissForm) {
    dismissForm.addEventListener('submit', function () {
      onboardingDialog.close();
    });
  }
})();