document.addEventListener('DOMContentLoaded', () => {
  const choices = document.querySelectorAll('.role-choice');
  const panels = document.querySelectorAll('.form-step');
  const role = document.getElementById('role');

  function setRole(value) {
    role.value = value;
    choices.forEach(button => button.classList.toggle('active', button.dataset.role === value));
    panels.forEach(panel => {
      const active = panel.dataset.panel === value;
      panel.classList.toggle('active', active);
      panel.querySelectorAll('input, select, textarea').forEach(field => {
        if (field.name !== 'password' && field.name !== 'confirm_password') field.disabled = !active;
      });
    });
  }

  choices.forEach(button => button.addEventListener('click', () => setRole(button.dataset.role)));
  setRole(role?.value || 'student');
});
