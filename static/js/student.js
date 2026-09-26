document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector("[data-student-search]");
  const type = document.querySelector("[data-student-type]");
  const cards = [...document.querySelectorAll("[data-opportunity-card]")];
  const filter = () => {
    const term = (search?.value || "").trim().toLowerCase();
    const selectedType = type?.value || "";
    let visible = 0;
    cards.forEach((card) => {
      const show = (!term || card.textContent.toLowerCase().includes(term)) &&
                   (!selectedType || card.dataset.type === selectedType);
      card.hidden = !show;
      if (show) visible += 1;
    });
    const count = document.querySelector("[data-opportunity-count]");
    if (count) count.textContent = visible + " opportunit" + (visible === 1 ? "y" : "ies");
  };
  search?.addEventListener("input", filter);
  type?.addEventListener("change", filter);
  const editor = document.querySelector("[data-profile-edit]");
  const fieldset = document.getElementById("profile-editor");
  const actions = document.querySelector("[data-profile-actions]");
  const cancel = document.querySelector("[data-profile-cancel]");
  editor?.addEventListener("click", () => {
    if (!fieldset) return;
    fieldset.disabled = false;
    editor.hidden = true;
    if (actions) actions.hidden = false;
    const firstField = fieldset.querySelector("input:not([type='hidden']), select, textarea");
    firstField?.focus();
  });
  cancel?.addEventListener("click", () => window.location.reload());

  document.querySelectorAll("[data-application-status]").forEach((select) => {
    const rows = [...document.querySelectorAll("[data-application-row]")];
    select.addEventListener("change", () => {
      const value = select.value.toLowerCase();
      rows.forEach((row) => { row.hidden = Boolean(value) && row.dataset.status !== value; });
    });
  });
});
