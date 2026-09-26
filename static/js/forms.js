document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-client-validate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); }
    });
  });
  const localIsoDate = (date = new Date()) => {
    const offset = date.getTimezoneOffset();
    const local = new Date(date.getTime() - offset * 60 * 1000);
    return local.toISOString().slice(0, 10);
  };

  document.querySelectorAll('input[type="date"][data-min-today]').forEach((input) => {
    input.min = localIsoDate();
  });
});
