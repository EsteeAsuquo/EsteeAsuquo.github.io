document.addEventListener('DOMContentLoaded', () => {
  // Copyright year
  const yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // Mobile nav toggle
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');
  navToggle?.addEventListener('click', () => {
    const open = mainNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });

  // Highlight active nav link based on pathname (works across separate pages)
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.main-nav a').forEach((a) => {
    const href = a.getAttribute('href') || '';
    const target = href === '' ? 'index.html' : href;
    const filename = target.split('/').pop();
    if (filename === current || (current === '' && filename === 'index.html')) {
      a.classList.add('active');
    } else {
      a.classList.remove('active');
    }
    // close mobile nav when a link is clicked
    a.addEventListener('click', () => {
      if (mainNav.classList.contains('open')) {
        mainNav.classList.remove('open');
      }
    });
  });

  // subscribe form (no backend)
  const form = document.getElementById('subscribeForm');
  const msg = document.getElementById('formMsg');
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('subEmail')?.value;
    if (!email) {
      if (msg) {
        msg.textContent = 'Please enter a valid email.';
      }
      return;
    }
    if (msg) {
      msg.textContent = 'Thanks — you are subscribed!';
    }
    form.reset();
    setTimeout(() => {
      if (msg) {
        msg.textContent = '';
      }
    }, 3500);
  });
});
