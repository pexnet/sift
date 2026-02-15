import DOMPurify from "dompurify";

const ALLOWED_TAGS = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "p",
  "br",
  "ul",
  "ol",
  "li",
  "blockquote",
  "pre",
  "code",
  "a",
  "strong",
  "em",
  "b",
  "i",
  "hr",
] as const;

const ALLOWED_ATTR = ["href", "title", "lang", "dir"] as const;

function normalizeLinks(html: string): string {
  const container = document.createElement("div");
  container.innerHTML = html;

  container.querySelectorAll("a").forEach((anchor) => {
    const href = anchor.getAttribute("href")?.trim() ?? "";
    if (!href) {
      anchor.removeAttribute("href");
      anchor.removeAttribute("target");
      anchor.removeAttribute("rel");
      return;
    }

    anchor.setAttribute("target", "_blank");
    anchor.setAttribute("rel", "noopener noreferrer");
  });

  return container.innerHTML;
}

function escapeHtml(input: string): string {
  return input
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function isLikelyHtml(input: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(input);
}

export function sanitizeArticleHtml(input: string): string {
  const sanitized = DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [...ALLOWED_TAGS],
    ALLOWED_ATTR: [...ALLOWED_ATTR],
    FORBID_TAGS: ["style", "script", "iframe", "object", "embed", "form"],
  });

  if (typeof sanitized !== "string") {
    return "";
  }

  return normalizeLinks(sanitized).trim();
}

export function toReaderHtml(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) {
    return "";
  }

  if (isLikelyHtml(trimmed)) {
    return sanitizeArticleHtml(trimmed);
  }

  const normalized = trimmed.replaceAll("\r\n", "\n");
  const paragraphs = normalized
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => `<p>${escapeHtml(part).replaceAll("\n", "<br />")}</p>`)
    .join("");

  return sanitizeArticleHtml(paragraphs);
}
