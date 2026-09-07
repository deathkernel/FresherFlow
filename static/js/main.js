document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.reveal').forEach((element, index) => {
    element.style.animationDelay = `${Math.min(index * 70, 420)}ms`;
  });

  const toasts = document.querySelectorAll('.toast-card');

  toasts.forEach((toast, index) => {
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px)';
      toast.style.transition = '.3s';

      setTimeout(() => toast.remove(), 300);
    }, 3200 + index * 250);
  });
});
