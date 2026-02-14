const THEME_KEY = "sift-theme";
const DENSITY_KEY = "sift-density";

function applyTheme(theme) {
  const resolved = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", resolved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
}

function applyDensity(value) {
  const workspace = document.querySelector(".workspace");
  if (!workspace) {
    return;
  }
  workspace.dataset.density = value === "comfortable" ? "comfortable" : "compact";
}

function getRows() {
  return Array.from(document.querySelectorAll("[data-article-row]"));
}

function syncBulkSelection() {
  const selectedIds = Array.from(document.querySelectorAll("[data-select-article]:checked")).map((item) => item.value);
  const serialized = selectedIds.join(",");
  for (const input of document.querySelectorAll("[data-bulk-ids]")) {
    if (input instanceof HTMLInputElement) {
      input.value = serialized;
    }
  }
  for (const button of document.querySelectorAll("[data-requires-selection]")) {
    if (button instanceof HTMLButtonElement) {
      button.disabled = selectedIds.length === 0;
    }
  }
}

function getSelectedRow() {
  return document.querySelector(".article-row.selected");
}

function setSelectedRow(row) {
  for (const current of getRows()) {
    current.classList.remove("selected");
  }
  row.classList.add("selected");
}

function moveSelection(delta) {
  const rows = getRows();
  if (rows.length === 0) {
    return;
  }
  const selected = getSelectedRow();
  const currentIndex = selected ? rows.indexOf(selected) : 0;
  const nextIndex = Math.max(0, Math.min(rows.length - 1, currentIndex + delta));
  setSelectedRow(rows[nextIndex]);
}

function openSelectedArticle() {
  const selected = getSelectedRow();
  if (!selected) {
    return;
  }
  const link = selected.querySelector(".row-main");
  if (link instanceof HTMLElement) {
    link.click();
  }
}

function toggleSelectedAction(selector) {
  const selected = getSelectedRow();
  if (!selected) {
    return;
  }
  const button = selected.querySelector(selector);
  if (button instanceof HTMLElement) {
    button.click();
  }
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const row = target.closest("[data-article-row]");
  if (row instanceof HTMLElement) {
    setSelectedRow(row);
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  if (target.matches("[data-select-article]")) {
    syncBulkSelection();
  }

  if (target.id === "state-select" || target.id === "sort-select") {
    const form = document.getElementById("article-filter-form");
    if (form instanceof HTMLFormElement && window.htmx) {
      window.htmx.trigger(form, "submit");
    }
  }
});

document.addEventListener("keydown", (event) => {
  const target = event.target;
  const tagName = target instanceof HTMLElement ? target.tagName : "";
  if (tagName === "INPUT" || tagName === "TEXTAREA" || target?.isContentEditable) {
    return;
  }

  if (event.key === "j") {
    event.preventDefault();
    moveSelection(1);
  } else if (event.key === "k") {
    event.preventDefault();
    moveSelection(-1);
  } else if (event.key === "o") {
    event.preventDefault();
    openSelectedArticle();
  } else if (event.key === "m") {
    event.preventDefault();
    toggleSelectedAction("[data-action='toggle-read']");
  } else if (event.key === "s") {
    event.preventDefault();
    toggleSelectedAction("[data-action='toggle-star']");
  } else if (event.key === "/") {
    event.preventDefault();
    const search = document.getElementById("article-search");
    if (search instanceof HTMLElement) {
      search.focus();
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const savedTheme = localStorage.getItem(THEME_KEY);
  applyTheme(savedTheme || "light");

  const toggle = document.getElementById("theme-toggle");
  if (toggle instanceof HTMLElement) {
    toggle.addEventListener("click", toggleTheme);
  }

  const savedDensity = localStorage.getItem(DENSITY_KEY) || "compact";
  applyDensity(savedDensity);

  const density = document.getElementById("density-select");
  if (density instanceof HTMLSelectElement) {
    density.value = savedDensity;
    density.addEventListener("change", () => {
      localStorage.setItem(DENSITY_KEY, density.value);
      applyDensity(density.value);
    });
  }

  syncBulkSelection();
});

document.body.addEventListener("htmx:afterSwap", () => {
  const selected = getSelectedRow();
  if (!selected) {
    const rows = getRows();
    if (rows.length > 0) {
      setSelectedRow(rows[0]);
    }
  }
  syncBulkSelection();
});
