document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".reveal").forEach((element, index) => {
    element.style.animationDelay =
      Math.min(index * 70, 420) + "ms";
  });

  document
    .querySelectorAll(
      ".workspace .stat-card, .workspace .panel, .workspace .job-card"
    )
    .forEach((element, index) => {
      element.classList.add("ui-enter");
      element.style.setProperty(
        "--enter-delay",
        Math.min(index * 45, 260) + "ms"
      );
    });

  document.querySelectorAll(".toast-card").forEach((toast) => {
    let timeoutId;
    const dismiss = () => {
      window.clearTimeout(timeoutId);
      toast.classList.add("is-dismissing");
      window.setTimeout(() => toast.remove(), 250);
    };
    const scheduleDismiss = () => {
      window.clearTimeout(timeoutId);
      if (!toast.matches(".error, .danger")) {
        timeoutId = window.setTimeout(dismiss, 7000);
      }
    };
    toast.querySelector(".toast-dismiss")?.addEventListener("click", dismiss);
    toast.addEventListener("mouseenter", () => window.clearTimeout(timeoutId));
    toast.addEventListener("mouseleave", scheduleDismiss);
    toast.addEventListener("focusin", () => window.clearTimeout(timeoutId));
    toast.addEventListener("focusout", scheduleDismiss);
    scheduleDismiss();
  });

  document.querySelectorAll("[data-step-form]").forEach((form) => {
    const steps = [...form.querySelectorAll("[data-step]")];
    const indicators = [
      ...document.querySelectorAll(
        '[data-stepper="' + form.id + '"] [data-step-indicator]'
      ),
    ];
    const backButtons = [...form.querySelectorAll("[data-step-back]")];
    const nextButtons = [...form.querySelectorAll("[data-step-next]")];
    let current = 0;

    const showStep = (index) => {
      current = Math.max(0, Math.min(index, steps.length - 1));

      steps.forEach((step, i) => {
        step.hidden = i !== current;
      });

      indicators.forEach((item, i) => {
        item.classList.toggle("active", i === current);
        item.classList.toggle("complete", i < current);
        if (i === current) {
          item.setAttribute("aria-current", "step");
        } else {
          item.removeAttribute("aria-current");
        }
      });

      backButtons.forEach((button) => {
        button.hidden = current === 0;
      });

      nextButtons.forEach((button) => {
        button.hidden = current === steps.length - 1;
      });

      const firstField = steps[current]?.querySelector(
        "input, select, textarea"
      );
      firstField?.focus({ preventScroll: true });
    };

    const validateStep = () => {
      const fields =
        steps[current]?.querySelectorAll(
          "input, select, textarea"
        ) || [];

      for (const field of fields) {
        if (!field.checkValidity()) {
          field.reportValidity();
          return false;
        }
      }

      return true;
    };

    nextButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (validateStep()) {
          showStep(current + 1);
        }
      });
    });

    backButtons.forEach((button) => {
      button.addEventListener("click", () => {
        showStep(current - 1);
      });
    });

    indicators.forEach((item, index) => {
      item.addEventListener("click", () => {
        if (index <= current || validateStep()) {
          showStep(index);
        }
      });
    });

    showStep(0);
  });

  document.querySelectorAll("[data-confirm]").forEach((control) => {
    control.addEventListener("click", (event) => {
      const message =
        control.dataset.confirm ||
        "Are you sure you want to continue?";

      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-filter-input]").forEach((input) => {
    const selector = input.dataset.filterInput;
    const items = [...document.querySelectorAll(selector)];

    input.addEventListener("input", () => {
      const term = input.value.trim().toLowerCase();

      items.forEach((item) => {
        item.hidden =
          Boolean(term) &&
          !item.textContent.toLowerCase().includes(term);
      });
    });
  });
});
