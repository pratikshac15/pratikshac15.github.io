const thoughts = [...document.querySelectorAll('.thought')];
const key = document.getElementById('thoughtKey');
const question = document.getElementById('thoughtQ');
const copy = document.getElementById('thoughtCopy');

function activateThought(button) {
  thoughts.forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  key.textContent = button.dataset.key;
  question.textContent = button.dataset.q;
  copy.textContent = button.dataset.copy;
}

thoughts.forEach(button => {
  button.addEventListener('mouseenter', () => activateThought(button));
  button.addEventListener('focus', () => activateThought(button));
  button.addEventListener('click', () => activateThought(button));
});

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll('.story, .paper, .presentation, .people-notes article, .gallery figure, .sketch-gallery figure')
    .forEach(element => observer.observe(element));
}
