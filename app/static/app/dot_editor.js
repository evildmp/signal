(function () {
  function getDotIdFromEditUrl(editUrl) {
    var match = (editUrl || "").match(/^\/dot\/(\d+)\/edit\/$/);
    return match ? match[1] : "";
  }

  function getStoredOwnershipToken(form) {
    try {
      var tokens = JSON.parse(localStorage.getItem("dotTokens") || "{}");
      var dotId = getDotIdFromEditUrl(form.getAttribute("hx-post"));
      if (!dotId) return "";
      return tokens[dotId] || "";
    } catch (error) {
      return "";
    }
  }

  function wireSentimentPicker(form, picker) {
    var freeTextName = picker.dataset.freeTextFor;
    var freeTextInput = form.querySelector(
      'input[type="hidden"][name="' + freeTextName + '"]'
    );
    var chipList = form.querySelector('[data-chip-list-for="' + freeTextName + '"]');
    var chipInput = form.querySelector(
      '[data-chip-input-for="' + freeTextName + '"]'
    );
    var defaultPlaceholder = chipInput
      ? chipInput.getAttribute("placeholder") || ""
      : "";
    var checkboxes = picker.querySelectorAll('input[type="checkbox"]');

    if (!freeTextInput || !chipList || !chipInput || !checkboxes.length) return;

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

    function createChip(value, isPreset) {
      var chip = document.createElement("span");
      chip.className = "p-chip is-inline is-dense dot-editor-chip";
      chip.dataset.value = value;
      chip.dataset.preset = isPreset ? "1" : "0";

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "p-chip__dismiss dot-editor-chip-remove";
      remove.setAttribute("aria-label", "Remove " + value);
      remove.textContent = "x";

      var text = document.createElement("span");
      text.className = "p-chip__value dot-editor-chip-text";
      text.textContent = value;

      remove.addEventListener("click", function () {
        removeValue(value);
      });

      chip.appendChild(remove);
      chip.appendChild(text);
      chipList.appendChild(chip);
    }

    function render() {
      var values = getValues();
      chipList.innerHTML = "";
      values.forEach(function (value) {
        var hasMatchingCheckbox = Array.from(checkboxes).some(function (checkbox) {
          return checkbox.value === value;
        });
        createChip(value, hasMatchingCheckbox);
      });

      checkboxes.forEach(function (checkbox) {
        var option = checkbox.closest(".dot-editor-sentiment-option");
        var selected = hasValue(values, checkbox.value);
        checkbox.checked = selected;
        if (option) {
          option.classList.toggle("is-selected", selected);
        }
      });

      chipInput.setAttribute("placeholder", values.length ? "" : defaultPlaceholder);
    }

    function setSingleValue(value) {
      var trimmed = value.trim();
      if (!trimmed) return;
      setValues([trimmed]);
      render();
    }

    function removeValue(value) {
      var values = getValues().filter(function (item) {
        return item !== value;
      });
      setValues(values);
      render();
    }

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) {
          setSingleValue(checkbox.value);
        } else {
          removeValue(checkbox.value);
        }
      });
    });

    chipInput.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== ",") return;
      event.preventDefault();
      setSingleValue(chipInput.value);
      chipInput.value = "";
    });

    chipInput.addEventListener("blur", function () {
      if (!chipInput.value.trim()) return;
      setSingleValue(chipInput.value);
      chipInput.value = "";
    });

    checkboxes.forEach(function (checkbox) {
      if (checkbox.checked) {
        setSingleValue(checkbox.value);
      }
    });

    render();
  }

  function initDotEditorForm(form) {
    if (!form || form.dataset.dotEditorBound === "1") return;
    form.dataset.dotEditorBound = "1";

    var privateCheckbox = form.querySelector('input[name="private"]');
    var teamFieldName = form.dataset.teamFieldName || "team_ids";
    var teamCheckboxes = form.querySelectorAll(
      'input[name="' + teamFieldName + '"]'
    );
    var ownershipTokenInput = form.querySelector('input[name="ownership_token"]');
    var deleteButton = form.querySelector("[data-delete-dot]");

    if (!privateCheckbox) return;

    function syncOwnershipToken() {
      if (!ownershipTokenInput) return;
      var token = getStoredOwnershipToken(form);
      var dialog = form.closest("#dot-editor-dialog");
      var isOwnedByUser = dialog && dialog.dataset.dotOwnedByUser === "1";

      ownershipTokenInput.value = token;
      if (deleteButton) {
        deleteButton.setAttribute(
          "hx-vals",
          JSON.stringify({ ownership_token: token })
        );
        deleteButton.disabled = !token && !isOwnedByUser;
      }
    }

    function syncPrivateFromTeams() {
      var hasTeamSelection = Array.from(teamCheckboxes).some(function (checkbox) {
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
      syncOwnershipToken();
      syncPrivateFromTeams();
      clearTeamsWhenPrivateChecked();
    });

    syncOwnershipToken();
  }

  document.addEventListener("htmx:afterSwap", function (e) {
    if (!e.detail.target || e.detail.target.id !== "dot-editor-host") return;
    var form = e.detail.target.querySelector("#dot-editor-form");
    initDotEditorForm(form);
  });
})();
