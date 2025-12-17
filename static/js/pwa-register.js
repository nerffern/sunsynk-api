(function () {
  if (!('serviceWorker' in navigator)) {
    console.warn('Service workers are not supported by this browser.');
    return;
  }

  const register = () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .catch(error => console.error('Service worker registration failed:', error));
  };

  if (document.readyState === 'complete') {
    register();
  } else {
    window.addEventListener('load', register);
  }
})();
