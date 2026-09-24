document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".candidate-actions select").forEach((select) => {
    select.addEventListener("change", () => select.closest("form")?.querySelector("button")?.focus());
  });
  const vacancyFilter = document.querySelector("[data-vacancy-filter]");
  const vacancies = [...document.querySelectorAll("[data-vacancy-row]")];
  vacancyFilter?.addEventListener("change", () => {
    const value = vacancyFilter.value.toLowerCase();
    vacancies.forEach((row) => { row.hidden = Boolean(value) && row.dataset.status !== value; });
  });
  const candidateSearch = document.querySelector("[data-candidate-search]");
  const candidates = [...document.querySelectorAll("[data-candidate-card]")];
  candidateSearch?.addEventListener("input", () => {
    const term = candidateSearch.value.trim().toLowerCase();
    candidates.forEach((card) => { card.hidden = Boolean(term) && !card.textContent.toLowerCase().includes(term); });
  });
});
