(() => {
  const container = document.getElementById('toast-container');
  if (!container) {
    return;
  }

  const showToast = (message, type = 'success') => {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    window.setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-6px)';
      window.setTimeout(() => toast.remove(), 200);
    }, 3000);
  };

  window.showToast = showToast;
})();
