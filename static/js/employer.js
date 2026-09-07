document.querySelectorAll('.candidate-actions select').forEach((select) => {
  select.addEventListener('change', () => {
    const form = select.closest('form');
    const button = form?.querySelector('button');

    button?.focus();
  });
});
