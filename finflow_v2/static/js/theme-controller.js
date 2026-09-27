(() => {
  const storageKey = 'finflow-theme';
  const legacyStorageKey = 'theme';
  const validThemes = new Set(['light', 'dark', 'system']);
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  const getDefaultTheme = () => document.documentElement.dataset.themeDefault || 'system';

  const getPreference = () => {
    const storedTheme = localStorage.getItem(storageKey) || localStorage.getItem(legacyStorageKey);
    return validThemes.has(storedTheme) ? storedTheme : getDefaultTheme();
  };

  const resolvedTheme = preference => (
    preference === 'system' ? (mediaQuery.matches ? 'dark' : 'light') : preference
  );

  const syncControls = preference => {
    document.querySelectorAll('[data-theme-option]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.themeOption === preference));
    });
    document.querySelectorAll('[data-theme-icon]').forEach(icon => {
      icon.textContent = preference === 'light' ? '☀️' : preference === 'dark' ? '🌙' : '◐';
    });
  };

  const applyTheme = preference => {
    const safePreference = validThemes.has(preference) ? preference : 'system';
    document.documentElement.dataset.theme = resolvedTheme(safePreference);
    document.documentElement.dataset.themePreference = safePreference;
    document.documentElement.style.colorScheme = document.documentElement.dataset.theme;
    syncControls(safePreference);
  };

  const persistTheme = preference => {
    if (document.body.dataset.themePersist !== 'true') return;
    const csrfTokenElement = document.getElementById('csrfTokenData');
    const csrfToken = csrfTokenElement ? JSON.parse(csrfTokenElement.textContent || 'null') : null;
    fetch('/api/theme', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken || '',
      },
      body: JSON.stringify({ theme: preference }),
    }).catch(() => undefined);
  };

  const setTheme = (preference, persist = true) => {
    const safePreference = validThemes.has(preference) ? preference : 'system';
    localStorage.setItem(storageKey, safePreference);
    localStorage.removeItem(legacyStorageKey);
    applyTheme(safePreference);
    if (persist) persistTheme(safePreference);
  };

  const closePicker = picker => {
    picker.classList.remove('is-open');
    picker.querySelector('[data-theme-picker-trigger]')?.setAttribute('aria-expanded', 'false');
    const menu = picker.querySelector('.theme-picker-menu');
    if (menu) menu.hidden = true;
  };

  const togglePicker = picker => {
    if (!picker) return;
    const menu = picker.querySelector('.theme-picker-menu');
    const isOpen = !picker.classList.contains('is-open');
    document.querySelectorAll('[data-theme-picker]').forEach(closePicker);
    if (!isOpen) return;
    picker.classList.add('is-open');
    picker.querySelector('[data-theme-picker-trigger]')?.setAttribute('aria-expanded', 'true');
    if (menu) menu.hidden = false;
  };

  const initialize = () => {
    const isSignedIn = document.body.dataset.themePersist === 'true';
    const preference = isSignedIn ? getDefaultTheme() : getPreference();
    if (isSignedIn) localStorage.setItem(storageKey, preference);
    applyTheme(preference);

    document.querySelectorAll('[data-theme-option]').forEach(button => {
      button.addEventListener('click', () => {
        setTheme(button.dataset.themeOption);
        const picker = button.closest('[data-theme-picker]');
        if (picker) closePicker(picker);
      });
    });

    document.querySelectorAll('[data-theme-picker-trigger]').forEach(button => {
      button.addEventListener('click', () => togglePicker(button.closest('[data-theme-picker]')));
    });

    document.addEventListener('click', event => {
      if (!event.target.closest('[data-theme-picker]')) {
        document.querySelectorAll('[data-theme-picker]').forEach(closePicker);
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        document.querySelectorAll('[data-theme-picker]').forEach(closePicker);
      }
    });
  };

  mediaQuery.addEventListener?.('change', () => {
    if (document.documentElement.dataset.themePreference === 'system') applyTheme('system');
  });

  window.FinFlowTheme = { applyTheme, getPreference, setTheme };
  document.addEventListener('DOMContentLoaded', initialize);
})();
