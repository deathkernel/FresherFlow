document.querySelectorAll('.filter-bar input').forEach((input) => {
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      input.form?.submit();
    }
  });
});
