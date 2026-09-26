document.addEventListener("DOMContentLoaded", () => {
  const landing = document.querySelector(".landing");
  if (!landing) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const progress = document.querySelector("[data-scroll-progress]");
  const nav = document.querySelector(".landing-nav");
  let ticking = false;

  const updateScrollState = () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const ratio = Math.min(1, Math.max(0, scrollTop / maxScroll));

    if (progress) {
      progress.style.transform = `scaleX(${ratio})`;
    }

    if (nav) {
      nav.classList.toggle("is-scrolled", scrollTop > 12);
    }

    ticking = false;
  };

  const requestScrollState = () => {
    if (!ticking) {
      window.requestAnimationFrame(updateScrollState);
      ticking = true;
    }
  };

  updateScrollState();
  window.addEventListener("scroll", requestScrollState, { passive: true });

  if (reduceMotion) return;

  const hero = landing.querySelector(".home-hero");
  const visual = landing.querySelector(".hero-visual");

  if (hero && visual) {
    hero.addEventListener("pointermove", (event) => {
      const rect = hero.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;

      visual.style.setProperty("--pointer-x", `${x * 10}px`);
      visual.style.setProperty("--pointer-y", `${y * 8}px`);
      visual.style.setProperty("--pointer-tilt-x", `${x * 1.8}deg`);
      visual.style.setProperty("--pointer-tilt-y", `${y * -1.4}deg`);
    }, { passive: true });

    hero.addEventListener("pointerleave", () => {
      visual.style.setProperty("--pointer-x", "0px");
      visual.style.setProperty("--pointer-y", "0px");
      visual.style.setProperty("--pointer-tilt-x", "0deg");
      visual.style.setProperty("--pointer-tilt-y", "0deg");
    });
  }

  landing.querySelectorAll(".tilt-card").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
      if (window.innerWidth < 760) return;

      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;

      card.style.setProperty("--tilt-x", `${x * 4}deg`);
      card.style.setProperty("--tilt-y", `${y * -4}deg`);
      card.style.setProperty("--lift", "-4px");
      card.style.setProperty("--spot-x", `${(x + 0.5) * 100}%`);
      card.style.setProperty("--spot-y", `${(y + 0.5) * 100}%`);
      card.classList.add("is-tilting");
    });

    card.addEventListener("pointerleave", () => {
      card.style.setProperty("--tilt-x", "0deg");
      card.style.setProperty("--tilt-y", "0deg");
      card.style.setProperty("--lift", "0px");
      card.classList.remove("is-tilting");
    });
  });
});
