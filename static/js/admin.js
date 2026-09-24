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
});
