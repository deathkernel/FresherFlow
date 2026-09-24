document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-client-validate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); }
    });
  });
  document.querySelectorAll('input[type="date"][data-min-today]').forEach((input) => {
    input.min = new Date().toISOString().slice(0, 10);
  });
});
