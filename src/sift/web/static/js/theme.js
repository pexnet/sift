(() => {
  const THEME_KEY = "sift-theme";

  function getTheme() {
    return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  function updateToggleLabel(button, theme) {
    button.textContent = theme === "dark" ? "Light" : "Dark";
    button.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
  }

  function setupThemeToggle() {
    const toggleButton = document.getElementById("theme-toggle");
    if (!(toggleButton instanceof HTMLButtonElement)) {
      return;
    }

    updateToggleLabel(toggleButton, getTheme());
    toggleButton.addEventListener("click", () => {
      const nextTheme = getTheme() === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, nextTheme);
      applyTheme(nextTheme);
      updateToggleLabel(toggleButton, nextTheme);
    });
  }

  applyTheme(getTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupThemeToggle, { once: true });
  } else {
    setupThemeToggle();
  }
})();
