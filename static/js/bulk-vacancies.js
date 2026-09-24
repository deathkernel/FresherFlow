document.addEventListener("DOMContentLoaded", () => {
  const body = document.getElementById("vacancy-rows");
  const template = document.getElementById("vacancy-row-template");
  const addButton = document.getElementById("add-vacancy");
  const count = document.getElementById("vacancy-count");
  if (!body || !template || !addButton || !count) return;
  const refresh = () => {
    const rows = [...body.querySelectorAll(".bulk-vacancy-row")];
    rows.forEach((row, index) => {
      row.querySelector(".bulk-row-number").textContent = index + 1;
      row.querySelector(".bulk-remove").style.visibility = rows.length === 1 ? "hidden" : "visible";
    });
    count.textContent = rows.length;
  };
  const addRow = () => {
    const fragment = template.content.cloneNode(true);
    const remove = fragment.querySelector(".bulk-remove");
    remove.addEventListener("click", () => { remove.closest("tr").remove(); refresh(); });
    body.appendChild(fragment);
    refresh();
    body.lastElementChild?.querySelector("input, select, textarea")?.focus();
  };
  addButton.addEventListener("click", addRow);
  document.getElementById("bulk-vacancy-form")?.addEventListener("submit", (event) => {
    if (!body.querySelector(".bulk-vacancy-row")) { event.preventDefault(); window.alert("Add at least one vacancy before publishing."); }
  });
  addRow();
});
