(function () {
  var onboardingDialog = document.getElementById('signal-onboarding-dialog');
  var onboardingContinue = document.getElementById('signal-onboarding-continue');
  var onboardingOpen = document.getElementById('signal-onboarding-open');

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

  if (onboardingContinue) {
    onboardingContinue.addEventListener('click', function () {
      var dismissUrl = onboardingDialog.dataset.dismissUrl;
      if (dismissUrl) {
        htmx.ajax('POST', dismissUrl, {
          swap: 'none',
          headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
          }
        });
      }
      onboardingDialog.close();
    });
  }
})();