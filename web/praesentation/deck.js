(() => {
  const stage = document.querySelector('.deck');
  const slides = [...stage.querySelectorAll(':scope > section')];
  const bar = document.querySelector('.deck-progress i');
  const count = document.querySelector('.deck-count');
  let current = 0;

  function fit() {
    const scale = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
    stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }

  function show(index) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach((slide, i) => {
      slide.classList.toggle('active', i === current);
      slide.setAttribute('aria-hidden', i === current ? 'false' : 'true');
    });
    bar.style.width = `${((current + 1) / slides.length) * 100}%`;
    count.textContent = `${current + 1} / ${slides.length}`;
    if (location.hash !== `#${current + 1}`) history.replaceState(null, '', `#${current + 1}`);
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => {});
  }

  document.addEventListener('keydown', (event) => {
    if (event.target.closest('input, select, textarea')) return;
    if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(event.key)) { event.preventDefault(); show(current + 1); }
    else if (['ArrowLeft', 'PageUp', 'Backspace'].includes(event.key)) { event.preventDefault(); show(current - 1); }
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(slides.length - 1);
    else if (event.key.toLowerCase() === 'f') toggleFullscreen();
  });

  document.querySelector('.deck-next').addEventListener('click', () => show(current + 1));
  document.querySelector('.deck-prev').addEventListener('click', () => show(current - 1));
  document.querySelector('.deck-full').addEventListener('click', toggleFullscreen);

  let touchX = null;
  document.addEventListener('touchstart', (event) => { touchX = event.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', (event) => {
    if (touchX === null) return;
    const delta = event.changedTouches[0].clientX - touchX;
    if (Math.abs(delta) > 50) show(current + (delta < 0 ? 1 : -1));
    touchX = null;
  });

  window.addEventListener('resize', fit);
  fit();
  show((parseInt(location.hash.slice(1), 10) || 1) - 1);
})();
