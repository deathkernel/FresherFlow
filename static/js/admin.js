document.addEventListener("DOMContentLoaded", () => {
  const confirmControls = document.querySelectorAll("[data-admin-confirm]");

  confirmControls.forEach((control) => {
    control.addEventListener("click", (event) => {
      const action = control.dataset.adminConfirm || "continue";

      if (!window.confirm("Are you sure you want to " + action + "?")) {
        event.preventDefault();
      }
    });
  });

  const search = document.querySelector("[data-admin-table-search]");
  const rows = [...document.querySelectorAll("[data-admin-row]")];

  search?.addEventListener("input", () => {
    const term = search.value.trim().toLowerCase();

    rows.forEach((row) => {
      row.hidden = Boolean(term) && !row.textContent.toLowerCase().includes(term);
    });
  });

  const bulkForm = document.querySelector("[data-bulk-moderation-form]");
  const selectAll = bulkForm?.querySelector("[data-job-select-all]");
  const jobChecks = [
    ...(bulkForm?.querySelectorAll("[data-job-select]") || []),
  ];
  const submitButton = bulkForm?.querySelector("[data-bulk-moderate-submit]");

  const syncBulkState = () => {
    const visibleChecks = jobChecks.filter(
      (checkbox) => !checkbox.closest("tr")?.hidden
    );
    const selectedVisible = visibleChecks.filter(
      (checkbox) => checkbox.checked
    );

    if (selectAll) {
      selectAll.checked =
        visibleChecks.length > 0 &&
        selectedVisible.length === visibleChecks.length;
      selectAll.indeterminate =
        selectedVisible.length > 0 &&
        selectedVisible.length < visibleChecks.length;
    }

    if (submitButton) {
      submitButton.disabled = jobChecks.every(
        (checkbox) => !checkbox.checked
      );
    }
  };

  selectAll?.addEventListener("change", () => {
    jobChecks.forEach((checkbox) => {
      if (!checkbox.closest("tr")?.hidden) {
        checkbox.checked = selectAll.checked;
      }
    });

    syncBulkState();
  });

  jobChecks.forEach((checkbox) => {
    checkbox.addEventListener("change", syncBulkState);
  });

  bulkForm?.addEventListener("submit", (event) => {
    const selected = jobChecks.filter((checkbox) => checkbox.checked);

    if (!selected.length) {
      event.preventDefault();
      window.alert("Select at least one job first.");
      return;
    }

    const decision =
      bulkForm.querySelector('select[name="decision"]')?.value || "rejected";
    const action = decision === "approved" ? "Approve" : "Reject";

    if (!window.confirm(action + " " + selected.length + " selected job(s)?")) {
      event.preventDefault();
    }
  });

  syncBulkState();
});
