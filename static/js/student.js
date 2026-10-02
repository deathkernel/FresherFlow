document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector("[data-student-search]");
  const type = document.querySelector("[data-student-type]");
  const cards = [...document.querySelectorAll("[data-opportunity-card]")];
  const count = document.querySelector("[data-opportunity-count]");

  const filterJobs = () => {
    const term = (search?.value || "").trim().toLowerCase();
    const selectedType = type?.value || "";
    let visible = 0;

    cards.forEach((card) => {
      const matchesSearch =
        !term || card.textContent.toLowerCase().includes(term);
      const matchesType =
        !selectedType || card.dataset.type === selectedType;
      const show = matchesSearch && matchesType;

      card.hidden = !show;

      if (show) {
        visible += 1;
      }
    });

    if (count) {
      count.textContent =
        visible + " opportunit" + (visible === 1 ? "y" : "ies");
    }
  };

  search?.addEventListener("input", filterJobs);
  type?.addEventListener("change", filterJobs);

  document.querySelectorAll("[data-application-status]").forEach((select) => {
    const rows = [...document.querySelectorAll("[data-application-row]")];

    select.addEventListener("change", () => {
      const status = select.value.toLowerCase();

      rows.forEach((row) => {
        row.hidden = Boolean(status) && row.dataset.status !== status;
      });
    });
  });
});
