document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".candidate-actions select").forEach((select) => {
    select.addEventListener("change", () => {
      select.closest("form")?.querySelector("button")?.focus();
    });
  });

  const vacancyFilter = document.querySelector("[data-vacancy-filter]");
  const vacancies = [...document.querySelectorAll("[data-vacancy-row]")];
  vacancyFilter?.addEventListener("change", () => {
    const value = vacancyFilter.value.toLowerCase();
    vacancies.forEach((row) => {
      row.hidden = Boolean(value) && row.dataset.status !== value;
    });
  });

  const candidateSearch = document.querySelector("[data-candidate-search]");
  const candidates = [...document.querySelectorAll("[data-candidate-card]")];
  candidateSearch?.addEventListener("input", () => {
    const term = candidateSearch.value.trim().toLowerCase();
    candidates.forEach((card) => {
      card.hidden = Boolean(term) && !card.textContent.toLowerCase().includes(term);
    });
  });

  const profileModal = document.querySelector("#candidateProfileModal");
  const setProfileText = (selector, value) => {
    const target = profileModal?.querySelector(selector);
    if (target) target.textContent = value || "Not added";
  };

  profileModal?.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget;
    const card = trigger?.closest("[data-candidate-card]");
    const data = card?.querySelector(".candidate-profile-data");
    if (!data) return;

    const get = (name, fallback = "Not added") =>
      data.querySelector(name)?.textContent?.trim() || fallback;

    const name = get("[data-profile-name]", "Candidate");
    const strength = Math.max(
      0,
      Math.min(100, Number(get("[data-profile-strength]", "20")) || 20),
    );

    setProfileText("#candidateProfileModalLabel", name);
    setProfileText("#candidateModalRole", get("[data-profile-role]", "Applied candidate"));
    setProfileText("#candidateModalEmail", get("[data-profile-email]"));
    setProfileText("#candidateModalPhone", get("[data-profile-phone]"));
    setProfileText("#candidateModalEducation", get("[data-profile-education]"));
    setProfileText("#candidateModalCollege", get("[data-profile-college]"));
    setProfileText("#candidateModalGraduation", get("[data-profile-graduation]"));
    setProfileText("#candidateModalJobType", get("[data-profile-job-type]"));
    setProfileText("#candidateModalLocation", get("[data-profile-location]"));
    setProfileText("#candidateModalSkills", get("[data-profile-skills]", "No skills added"));
    setProfileText("#candidateModalCertifications", get("[data-profile-certifications]", "No certifications added"));
    setProfileText("#candidateModalResume", get("[data-profile-resume]", "No resume uploaded"));
    setProfileText("#candidateModalStrength", String(strength));

    const bar = profileModal.querySelector("#candidateModalStrengthBar");
    if (bar) bar.style.width = strength + "%";

    const avatar = profileModal.querySelector("#candidateModalAvatar");
    if (avatar) {
      avatar.textContent = name.trim().slice(0, 1).toUpperCase() || "S";
    }
  });
});
