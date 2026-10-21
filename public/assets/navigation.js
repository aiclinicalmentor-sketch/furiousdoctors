document.querySelectorAll('.nav-dropdown').forEach((dropdown) => {
  const toggle = dropdown.querySelector('.nav-dropdown-toggle');
  const menu = dropdown.querySelector('.nav-dropdown-menu');
  const setOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    menu.hidden = !open;
  };
  dropdown.addEventListener('pointerenter', (event) => {
    if (event.pointerType === 'mouse') setOpen(true);
  });
  dropdown.addEventListener('pointerleave', (event) => {
    if (event.pointerType === 'mouse' && !dropdown.contains(document.activeElement)) setOpen(false);
  });
  toggle.addEventListener('click', () => setOpen(menu.hidden));
  toggle.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setOpen(true);
      menu.querySelector('a').focus();
    }
  });
  dropdown.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      toggle.focus();
      setOpen(false);
    }
  });
  dropdown.addEventListener('focusout', (event) => {
    if (!dropdown.contains(event.relatedTarget)) setOpen(false);
  });
  document.addEventListener('click', (event) => {
    if (!dropdown.contains(event.target)) setOpen(false);
  });
});
