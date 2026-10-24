// ---------- "Things I think about" topic switcher ----------
const thoughts = [...document.querySelectorAll('.thought')];
const key = document.getElementById('thoughtKey');
const question = document.getElementById('thoughtQ');
const copy = document.getElementById('thoughtCopy');

function activateThought(button) {
  thoughts.forEach(item => {
    item.classList.remove('active');
    item.setAttribute('aria-pressed', 'false');
  });
  button.classList.add('active');
  button.setAttribute('aria-pressed', 'true');
  key.textContent = button.dataset.key;
  question.textContent = button.dataset.q;
  copy.textContent = button.dataset.copy;
}

thoughts.forEach(button => {
  button.addEventListener('mouseenter', () => activateThought(button));
  button.addEventListener('focus', () => activateThought(button));
  button.addEventListener('click', () => activateThought(button));
});

// ---------- Menu for phones and small tablets ----------
const menuToggle = document.querySelector('.menu-toggle');
const navLinks = document.getElementById('navlinks');

function setMenu(open) {
  menuToggle.setAttribute('aria-expanded', String(open));
  navLinks.classList.toggle('open', open);
}

if (menuToggle && navLinks) {
  menuToggle.addEventListener('click', () => {
    setMenu(menuToggle.getAttribute('aria-expanded') !== 'true');
  });
  navLinks.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      menuToggle.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.nav')) setMenu(false);
  });
}

// ---------- Reveal on scroll ----------
const revealTargets = document.querySelectorAll(
  '.story, .build, .paper, .presentation, .people-notes article, .gallery figure, .sketch-gallery figure'
);
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (reduceMotion || !('IntersectionObserver' in window)) {
  revealTargets.forEach(element => element.classList.add('in'));
} else {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealTargets.forEach(element => observer.observe(element));
}
