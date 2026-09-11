const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.site-header nav');

menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  nav.classList.toggle('open', !isOpen);
});

document.querySelectorAll('.site-header a').forEach((link) => {
  link.addEventListener('click', () => {
    menuButton.setAttribute('aria-expanded', 'false');
    nav.classList.remove('open');
  });
});

document.querySelectorAll('.faq-item button').forEach((button) => {
  button.addEventListener('click', () => {
    const item = button.closest('.faq-item');
    const willOpen = !item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach((other) => {
      other.classList.remove('open');
      other.querySelector('button').setAttribute('aria-expanded', 'false');
    });
    if (willOpen) {
      item.classList.add('open');
      button.setAttribute('aria-expanded', 'true');
    }
  });
});

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add('visible'));
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));

// Hover previews; click pins a brief for touch, scrolling, and text selection.
(() => {
  let active = null;
  let pinned = false;
  let closeTimer;
  const cancelClose = () => clearTimeout(closeTimer);
  const position = () => {
    if (!active) return;
    const { button, panel } = active;
    const rect = button.getBoundingClientRect();
    const gap = 8;
    const margin = 12;
    const width = document.documentElement.clientWidth;
    const height = window.innerHeight;
    panel.style.maxHeight = `${Math.max(0, height - margin * 2)}px`;
    const panelWidth = panel.offsetWidth;
    const panelHeight = panel.offsetHeight;
    // Prefer beside the artwork; use below/above when the viewport is narrow.
    let left = rect.right + gap;
    let top = rect.top;
    if (left + panelWidth > width - margin) {
      left = rect.left - gap - panelWidth;
      if (left < margin) {
        left = rect.left;
        top = rect.bottom + gap;
        if (top + panelHeight > height - margin) top = rect.top - gap - panelHeight;
      }
    }
    panel.style.left = `${Math.max(margin, Math.min(left, width - panelWidth - margin))}px`;
    panel.style.top = `${Math.max(margin, Math.min(top, height - panelHeight - margin))}px`;
  };
  const close = () => {
    cancelClose();
    if (!active) return;
    const { button, panel } = active;
    active = null;
    pinned = false;
    if (panel.matches(':popover-open')) panel.hidePopover();
    panel.hidden = true;
    button.setAttribute('aria-expanded', 'false');
  };
  const open = (entry) => {
    cancelClose();
    if (active === entry) return;
    close();
    active = entry;
    entry.panel.hidden = false;
    entry.panel.showPopover?.();
    entry.button.setAttribute('aria-expanded', 'true');
    position();
  };
  const scheduleClose = () => {
    cancelClose();
    closeTimer = setTimeout(() => {
      if (!active || pinned) return;
      const focused = document.activeElement;
      if (focused === active.button || active.panel.contains(focused)) return;
      close();
    }, 200);
  };
  document.querySelectorAll('button[data-visual-placeholder]').forEach((button) => {
    const panel = document.getElementById(button.getAttribute('aria-controls'));
    const entry = { button, panel };
    // Top-layer popovers avoid clipping from animated cards. Moving the notes to
    // body also keeps the fallback out of the scenario card's two-column grid.
    document.body.append(panel);
    button.addEventListener('pointerenter', (event) => {
      if (event.pointerType === 'mouse' && !pinned) open(entry);
    });
    button.addEventListener('pointerleave', scheduleClose);
    button.addEventListener('focus', () => {
      if (button.matches(':focus-visible')) open(entry);
    });
    button.addEventListener('blur', scheduleClose);
    button.addEventListener('click', () => {
      if (active === entry && pinned) close();
      else { open(entry); pinned = true; }
    });
    panel.addEventListener('pointerenter', cancelClose);
    panel.addEventListener('pointerleave', scheduleClose);
    panel.addEventListener('focusout', scheduleClose);
    panel.querySelector('.design-brief-close').addEventListener('click', () => {
      button.focus({ preventScroll: true });
      close();
    });
  });
  document.addEventListener('pointerdown', (event) => {
    if (active && !active.button.contains(event.target) && !active.panel.contains(event.target)) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && active) {
      if (active.panel.contains(document.activeElement)) active.button.focus({ preventScroll: true });
      close();
    }
  });
  window.addEventListener('resize', position);
  window.addEventListener('scroll', position, { passive: true });
})();
