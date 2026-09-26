document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-admin-confirm]").forEach((control) => {
    control.addEventListener("click", (event) => {
      if (!window.confirm("Are you sure you want to " + (control.dataset.adminConfirm || "continue") + "?")) event.preventDefault();
    });
  });

  const search = document.querySelector("[data-admin-table-search]");
  const rows = [...document.querySelectorAll("[data-admin-row]")];
  search?.addEventListener("input", () => {
    const term = search.value.trim().toLowerCase();
    rows.forEach((row) => { row.hidden = Boolean(term) && !row.textContent.toLowerCase().includes(term); });
  });

  const bulkForm = document.querySelector("[data-bulk-moderation-form]");
  const selectAll = bulkForm?.querySelector("[data-job-select-all]");
  const jobChecks = [...(bulkForm?.querySelectorAll("[data-job-select]") || [])];
  const bulkSubmit = bulkForm?.querySelector("[data-bulk-moderate-submit]");

  const syncBulkState = () => {
    const visibleChecks = jobChecks.filter((checkbox) => !checkbox.closest("tr")?.hidden);
    const selectedVisible = visibleChecks.filter((checkbox) => checkbox.checked);
    if (selectAll) {
      selectAll.checked = visibleChecks.length > 0 && selectedVisible.length === visibleChecks.length;
      selectAll.indeterminate = selectedVisible.length > 0 && selectedVisible.length < visibleChecks.length;
    }
    if (bulkSubmit) bulkSubmit.disabled = jobChecks.every((checkbox) => !checkbox.checked);
  };

  selectAll?.addEventListener("change", () => {
    jobChecks.forEach((checkbox) => {
      if (!checkbox.closest("tr")?.hidden) checkbox.checked = selectAll.checked;
    });
    syncBulkState();
  });

  jobChecks.forEach((checkbox) => checkbox.addEventListener("change", syncBulkState));

  bulkForm?.addEventListener("submit", (event) => {
    if (jobChecks.every((checkbox) => !checkbox.checked)) {
      event.preventDefault();
      window.alert("Select at least one job first.");
      return;
    }
    const decision = bulkForm.querySelector('select[name="decision"]')?.value;
    const count = jobChecks.filter((checkbox) => checkbox.checked).length;
    if (!window.confirm((decision === "approved" ? "Approve " : "Reject ") + count + " selected job(s)?")) {
      event.preventDefault();
    }
  });

  syncBulkState();
});
