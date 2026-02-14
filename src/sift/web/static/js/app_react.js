(function () {
  function parseSearch() {
    const params = new URLSearchParams(window.location.search);
    return {
      scope_type: params.get("scope_type") || "system",
      scope_id: params.get("scope_id") || "",
      state: params.get("state") || "all",
      sort: params.get("sort") || "newest",
      q: params.get("q") || "",
      article_id: params.get("article_id") || "",
      limit: params.get("limit") || "50",
      offset: params.get("offset") || "0",
    };
  }

  function toApiQuery(search) {
    const query = new URLSearchParams();
    query.set("scope_type", search.scope_type);
    if (search.scope_id) {
      query.set("scope_id", search.scope_id);
    }
    query.set("state", search.state);
    query.set("sort", search.sort);
    query.set("limit", search.limit);
    query.set("offset", search.offset);
    if (search.q) {
      query.set("q", search.q);
    }
    return query;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  function renderNav(root, navigation) {
    const navState = root.querySelector("#react-nav-state");
    const navList = root.querySelector("#react-nav-list");
    if (!(navState instanceof HTMLElement) || !(navList instanceof HTMLElement)) {
      return;
    }

    const topItems = [
      ...(navigation.system || []),
      ...(navigation.folders || []),
      ...(navigation.streams || []),
    ];

    if (topItems.length === 0) {
      navState.textContent = "No navigation items.";
      navList.hidden = true;
      return;
    }

    navList.innerHTML = "";
    for (const item of topItems) {
      const li = document.createElement("li");
      li.textContent = item.title || item.name || item.key || "Untitled";
      navList.appendChild(li);
    }

    navState.hidden = true;
    navList.hidden = false;
  }

  function renderArticles(root, articleList) {
    const state = root.querySelector("#react-list-state");
    const list = root.querySelector("#react-article-list");
    if (!(state instanceof HTMLElement) || !(list instanceof HTMLElement)) {
      return;
    }

    if (!Array.isArray(articleList.items) || articleList.items.length === 0) {
      state.textContent = "No articles found for this scope.";
      list.hidden = true;
      return null;
    }

    list.innerHTML = "";
    for (const article of articleList.items) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "react-article-button";
      button.textContent = article.title || "Untitled article";
      button.dataset.articleId = article.id;
      li.appendChild(button);
      list.appendChild(li);
    }

    state.hidden = true;
    list.hidden = false;
    return articleList.items[0]?.id ?? null;
  }

  function renderReader(root, detail) {
    const state = root.querySelector("#react-reader-state");
    const panel = root.querySelector("#react-reader");
    if (!(state instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
      return;
    }

    panel.innerHTML = "";
    const title = document.createElement("h3");
    title.textContent = detail.title || "Untitled article";
    panel.appendChild(title);

    const byline = document.createElement("p");
    byline.className = "muted";
    byline.textContent = detail.author || detail.feed_title || "";
    panel.appendChild(byline);

    const content = document.createElement("p");
    content.textContent = detail.content_text || "No content available.";
    panel.appendChild(content);

    state.hidden = true;
    panel.hidden = false;
  }

  async function bootstrap() {
    const root = document.getElementById("react-workspace-root");
    if (!(root instanceof HTMLElement)) {
      return;
    }

    const search = parseSearch();
    const query = toApiQuery(search).toString();
    const navEndpoint = root.dataset.navigationEndpoint;
    const articlesEndpoint = root.dataset.articlesEndpoint;
    const detailTemplate = root.dataset.articleEndpointTemplate || "";

    if (!navEndpoint || !articlesEndpoint || !detailTemplate) {
      return;
    }

    try {
      const navigation = await fetchJson(navEndpoint);
      renderNav(root, navigation);
    } catch (error) {
      const navState = root.querySelector("#react-nav-state");
      if (navState instanceof HTMLElement) {
        navState.textContent = "Failed to load navigation.";
      }
    }

    let selectedArticleId = search.article_id || null;
    try {
      const articleList = await fetchJson(`${articlesEndpoint}?${query}`);
      const firstId = renderArticles(root, articleList);
      if (!selectedArticleId) {
        selectedArticleId = firstId;
      }
    } catch (error) {
      const listState = root.querySelector("#react-list-state");
      if (listState instanceof HTMLElement) {
        listState.textContent = "Failed to load articles.";
      }
    }

    async function loadReader(articleId) {
      if (!articleId) {
        return;
      }
      try {
        const detail = await fetchJson(detailTemplate.replace("{article_id}", articleId));
        renderReader(root, detail);
      } catch (error) {
        const state = root.querySelector("#react-reader-state");
        if (state instanceof HTMLElement) {
          state.textContent = "Failed to load article details.";
        }
      }
    }

    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const button = target.closest(".react-article-button");
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }
      const articleId = button.dataset.articleId;
      if (articleId) {
        void loadReader(articleId);
      }
    });

    await loadReader(selectedArticleId);
  }

  document.addEventListener("DOMContentLoaded", () => {
    void bootstrap();
  });
})();
