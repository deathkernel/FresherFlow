document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector("[data-student-search]");
  const type = document.querySelector("[data-student-type]");
  const location = document.querySelector("[data-student-location]");
  const skill = document.querySelector("[data-student-skill]");
  const cards = [...document.querySelectorAll("[data-opportunity-card]")];
  const count = document.querySelector("[data-opportunity-count]");

  const filterJobs = () => {
    const term = (search?.value || "").trim().toLowerCase();
    const selectedType = type?.value || "";
    const selectedLocation = (location?.value || "").trim().toLowerCase();
    const selectedSkill = (skill?.value || "").trim().toLowerCase();
    let visible = 0;

    cards.forEach((card) => {
      const matchesSearch =
        !term || card.textContent.toLowerCase().includes(term);
      const matchesType =
        !selectedType || card.dataset.type === selectedType;
      const matchesLocation =
        !selectedLocation ||
        (card.dataset.location || "").toLowerCase().includes(selectedLocation);
      const matchesSkill =
        !selectedSkill ||
        (card.dataset.skills || "").toLowerCase().includes(selectedSkill);
      const show = matchesSearch && matchesType && matchesLocation && matchesSkill;

      card.hidden = !show;

      if (show) {
        visible += 1;
      }
    });

    if (count) {
      count.textContent = visible + " visible on this page";
    }
  };

  search?.addEventListener("input", filterJobs);
  type?.addEventListener("change", filterJobs);
  location?.addEventListener("input", filterJobs);
  skill?.addEventListener("input", filterJobs);

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
