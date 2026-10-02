document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".candidate-actions select").forEach((select) => {
    select.addEventListener("change", () => {
      select.closest("form")?.querySelector("button")?.focus();
    });
  });

  const vacancyFilter = document.querySelector("[data-vacancy-filter]");
  const vacancies = [...document.querySelectorAll("[data-vacancy-row]")];

  vacancyFilter?.addEventListener("change", () => {
    const status = vacancyFilter.value.toLowerCase();

    vacancies.forEach((row) => {
      row.hidden = Boolean(status) && row.dataset.status !== status;
    });
  });

  const candidateSearch = document.querySelector("[data-candidate-search]");
  const candidates = [...document.querySelectorAll("[data-candidate-card]")];

  candidateSearch?.addEventListener("input", () => {
    const term = candidateSearch.value.trim().toLowerCase();

    candidates.forEach((card) => {
      card.hidden =
        Boolean(term) && !card.textContent.toLowerCase().includes(term);
    });
  });

  const profileModal = document.querySelector("#candidateProfileModal");

  const setProfileText = (selector, value) => {
    const target = profileModal?.querySelector(selector);

    if (target) {
      target.textContent = value || "Not added";
    }
  };

  profileModal?.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget;
    const card = trigger?.closest("[data-candidate-card]");
    const data = card?.querySelector(".candidate-profile-data");

    if (!data) {
      return;
    }

    const getProfileValue = (selector, fallback = "Not added") => {
      return data.querySelector(selector)?.textContent?.trim() || fallback;
    };

    const name = getProfileValue("[data-profile-name]", "Candidate");
    const strength = Math.max(
      0,
      Math.min(
        100,
        Number(getProfileValue("[data-profile-strength]", "20")) || 20
      )
    );

    setProfileText("#candidateProfileModalLabel", name);
    setProfileText(
      "#candidateModalRole",
      getProfileValue("[data-profile-role]", "Applied candidate")
    );
    setProfileText("#candidateModalEmail", getProfileValue("[data-profile-email]"));
    setProfileText("#candidateModalPhone", getProfileValue("[data-profile-phone]"));
    setProfileText(
      "#candidateModalEducation",
      getProfileValue("[data-profile-education]")
    );
    setProfileText(
      "#candidateModalCollege",
      getProfileValue("[data-profile-college]")
    );
    setProfileText(
      "#candidateModalGraduation",
      getProfileValue("[data-profile-graduation]")
    );
    setProfileText(
      "#candidateModalJobType",
      getProfileValue("[data-profile-job-type]")
    );
    setProfileText(
      "#candidateModalLocation",
      getProfileValue("[data-profile-location]")
    );
    setProfileText(
      "#candidateModalSkills",
      getProfileValue("[data-profile-skills]", "No skills added")
    );
    setProfileText(
      "#candidateModalCertifications",
      getProfileValue(
        "[data-profile-certifications]",
        "No certifications added"
      )
    );
    setProfileText(
      "#candidateModalResume",
      getProfileValue("[data-profile-resume]", "No resume uploaded")
    );
    setProfileText("#candidateModalStrength", String(strength));

    const strengthBar = profileModal.querySelector(
      "#candidateModalStrengthBar"
    );
    if (strengthBar) {
      strengthBar.style.width = strength + "%";
    }

    const avatar = profileModal.querySelector("#candidateModalAvatar");
    if (avatar) {
      avatar.textContent = name.trim().slice(0, 1).toUpperCase() || "S";
    }
  });
});
