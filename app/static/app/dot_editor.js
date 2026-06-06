(function () {
  function getEditorFormOwnershipToken(form) {
    const dotId = form.dataset.dotId || '';
    if (!dotId) return '';
    return DotTokens.get(dotId);
  }

  function createChipList(freeTextInput, chipListElement, chipInput, checkboxes, defaultPlaceholder) {
    function getValues() {
      return freeTextInput.value
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
    }

    function setValues(values) {
      freeTextInput.value = values.join(", ");
    }

    function hasValue(values, value) {
      return values.indexOf(value) >= 0;
    }

    function buildChip(value, isPreset) {
      const chip = document.createElement("span");
      chip.className = "p-chip is-inline is-dense dot-editor-chip";
      chip.dataset.value = value;
      chip.dataset.preset = isPreset ? "1" : "0";

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "dot-editor-chip-remove";
      remove.setAttribute("aria-label", "Remove " + value);
      remove.textContent = "x";

      const text = document.createElement("span");
      text.className = "p-chip__value dot-editor-chip-text";
      text.textContent = value;

      remove.addEventListener("click", function () {
        self.remove(value);
      });

      chip.appendChild(remove);
      chip.appendChild(text);
      return chip;
    }

    function render() {
      const values = getValues();
      chipListElement.innerHTML = "";
      values.forEach(function (value) {
        const hasMatchingCheckbox = Array.from(checkboxes).some(function (checkbox) {
          return checkbox.value === value;
        });
        chipListElement.appendChild(buildChip(value, hasMatchingCheckbox));
      });

      checkboxes.forEach(function (checkbox) {
        const option = checkbox.closest(".dot-editor-sentiment-option");
        const selected = hasValue(values, checkbox.value);
        checkbox.checked = selected;
        if (option) {
          option.classList.toggle("is-selected", selected);
        }
      });

      chipInput.setAttribute("placeholder", values.length ? "" : defaultPlaceholder);
    }

    const self = {
      add: function (value) {
        const trimmed = value.trim();
        if (!trimmed) return;
        setValues([trimmed]);
        render();
      },
      remove: function (value) {
        const values = getValues().filter(function (item) {
          return item !== value;
        });
        setValues(values);
        render();
      },
      init: function () {
        checkboxes.forEach(function (checkbox) {
          if (checkbox.checked) {
            self.add(checkbox.value);
          }
        });
        render();
      }
    };

    return self;
  }

  function wireSentimentPicker(form, picker) {
    const freeTextName = picker.dataset.freeTextFor;
    const freeTextInput = form.querySelector(
      'input[type="hidden"][name="' + freeTextName + '"]'
    );
    const chipListElement = form.querySelector('[data-chip-list-for="' + freeTextName + '"]');
    const chipInput = form.querySelector(
      '[data-chip-input-for="' + freeTextName + '"]'
    );
    const defaultPlaceholder = chipInput
      ? chipInput.getAttribute("placeholder") || ""
      : "";
    const checkboxes = picker.querySelectorAll('input[type="checkbox"]');

    if (!freeTextInput || !chipListElement || !chipInput || !checkboxes.length) return;

    const chipList = createChipList(freeTextInput, chipListElement, chipInput, checkboxes, defaultPlaceholder);

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) {
          chipList.add(checkbox.value);
        } else {
          chipList.remove(checkbox.value);
        }
      });
    });

    chipInput.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== ",") return;
      event.preventDefault();
      chipList.add(chipInput.value);
      chipInput.value = "";
    });

    chipInput.addEventListener("blur", function () {
      if (!chipInput.value.trim()) return;
      chipList.add(chipInput.value);
      chipInput.value = "";
    });

    chipList.init();
  }

  function initDotEditorForm(form) {
    if (!form || form.dataset.dotEditorBound === "1") return;
    form.dataset.dotEditorBound = "1";

    const privateCheckbox = form.querySelector('input[name="private"]');
    const teamFieldName = form.dataset.teamFieldName || "team_ids";
    const teamCheckboxes = form.querySelectorAll(
      'input[name="' + teamFieldName + '"]'
    );
    const deleteButton = form.querySelector("[data-delete-dot]");

    if (!privateCheckbox) return;

    const cancelButton = form.querySelector(".dialog-cancel");
    if (cancelButton) {
      cancelButton.addEventListener("click", function () {
        const dialog = form.closest("dialog");
        if (dialog) dialog.close();
      });
    }

    function syncDeleteButtonState() {
      if (!deleteButton) return;
      const token = getEditorFormOwnershipToken(form);
      const dialog = form.closest("#dot-editor-dialog");
      const isOwnedByUser = dialog && dialog.dataset.dotOwnedByUser === "1";
      deleteButton.disabled = !token && !isOwnedByUser;
    }

    function syncPrivateFromTeams() {
      const hasTeamSelection = Array.from(teamCheckboxes).some(function (checkbox) {
        return checkbox.checked;
      });
      privateCheckbox.checked = !hasTeamSelection;
    }

    function clearTeamsWhenPrivateChecked() {
      if (!privateCheckbox.checked) return;
      teamCheckboxes.forEach(function (checkbox) {
        checkbox.checked = false;
      });
    }

    teamCheckboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", syncPrivateFromTeams);
    });

    privateCheckbox.addEventListener("change", clearTeamsWhenPrivateChecked);

    form
      .querySelectorAll(".dot-editor-sentiment-picker[data-free-text-for]")
      .forEach(function (picker) {
        wireSentimentPicker(form, picker);
      });

    form.addEventListener("submit", function () {
      syncDeleteButtonState();
      syncPrivateFromTeams();
      clearTeamsWhenPrivateChecked();
    });

    syncDeleteButtonState();
  }

  document.addEventListener("htmx:afterSwap", function (e) {
    if (!e.detail.target || e.detail.target.id !== "dot-editor-host") return;
    const form = e.detail.target.querySelector("#dot-editor-form");
    initDotEditorForm(form);
  });
})();
