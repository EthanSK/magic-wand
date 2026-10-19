// Finding the right How To guide for a question. Shared by the gallery page, tutorials/find.mjs
// and the tests, so a person searching the page and an agent answering a question get the same
// guide. It has no DOM code.

const STOP = new Set([
  "a", "an", "and", "are", "can", "do", "does", "for", "from", "get", "how", "i", "in", "is", "it", "me",
  "my", "of", "on", "or", "the", "this", "to", "use", "using", "wand", "what", "when", "where", "with", "you",
]);

// Spelling variants and everyday words, mapped onto the words the guides use.
const SYNONYMS = {
  cursor: "pointer", mouse: "pointer", centre: "center", centres: "center", centred: "center", recentre: "recenter",
  horizontal: "sideways", horizontally: "sideways", vertical: "updown", vertically: "updown",
  dictation: "dictate", speech: "dictate", voice: "dictate", talk: "dictate", speak: "dictate", transcribe: "dictate",
  commit: "stage", staging: "stage", submenu: "page", submenus: "page", menu: "hud",
  song: "music", songs: "music", media: "play", playback: "play", resume: "play",
  vscode: "vs", diff: "change", diffs: "change", cmd: "command", tab: "command",
};

function stem(word) {
  let w = word;
  if (w.length > 4 && w.endsWith("ies")) w = w.slice(0, -3) + "y";
  else if (w.length > 4 && /(ches|shes|xes|sses)$/.test(w)) w = w.slice(0, -2);
  else if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) w = w.slice(0, -1);
  if (w.length > 5 && w.endsWith("ing")) w = w.slice(0, -3);
  else if (w.length > 4 && w.endsWith("ed")) w = w.slice(0, -2);
  if (w.length > 3 && w.at(-1) === w.at(-2) && !"ls".includes(w.at(-1))) w = w.slice(0, -1);
  if (w.length > 4 && w.endsWith("e")) w = w.slice(0, -1);
  return w;
}

/** Normalised search words for a piece of text. */
export function words(text) {
  return String(text ?? "")
    .toLowerCase()
    .replace(/[’']/g, "")
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
    .map((word) => (word in SYNONYMS ? SYNONYMS[word] : word))
    .filter((word) => word && !STOP.has(word))
    .map(stem);
}

// Where a word appears decides how much it counts.
const FIELDS = [
  ["question", 3],
  ["questions", 2.5],
  ["keywords", 2],
  ["summary", 1],
  ["steps", 1],
  ["buttonNames", 1],
];
const index = new WeakMap();

function fieldWords(guide) {
  if (!index.has(guide)) {
    const join = (value) => (Array.isArray(value) ? value.join(" ") : value || "");
    index.set(guide, Object.fromEntries(FIELDS.map(([field]) => [field, new Set(words(join(guide[field])))])));
  }
  return index.get(guide);
}

/** Score one guide for a query; higher is better and 0 means no match. */
export function score(guide, query) {
  const terms = [...new Set(words(query))];
  if (!terms.length) return 0;
  const indexed = fieldWords(guide);
  let total = 0;
  let matched = 0;
  for (const term of terms) {
    let best = 0;
    for (const [field, weight] of FIELDS) {
      if (indexed[field].has(term)) best = Math.max(best, weight);
    }
    if (!best && term.length >= 4) {
      // Partly typed words, such as "scrol" or "dictat".
      for (const [field, weight] of FIELDS) {
        for (const candidate of indexed[field]) {
          if (candidate.startsWith(term) || (candidate.length >= 4 && term.startsWith(candidate))) best = Math.max(best, weight * 0.6);
        }
      }
    }
    if (best) matched += 1;
    total += best;
  }
  // Favour guides that cover the whole question over one shared word.
  return total * (matched / terms.length) ** 2;
}

export const MIN_SCORE = 1.5;

/** Guides matching a query, best first, as { guide, score }. An empty query keeps every guide in order. */
export function search(guides, query) {
  if (!words(query).length) return guides.map((guide) => ({ guide, score: 0 }));
  return guides
    .map((guide, order) => ({ guide, score: score(guide, query), order }))
    .filter((result) => result.score >= MIN_SCORE)
    .sort((a, b) => b.score - a.score || a.order - b.order)
    .map(({ guide, score: value }) => ({ guide, score: Math.round(value * 100) / 100 }));
}

/** The guides the gallery shows for a search and a button filter ("" for every button). */
export function filterGuides(guides, query, button = "") {
  return search(guides, query)
    .map(({ guide }) => guide)
    .filter((guide) => !button || guide.buttons.includes(button));
}

/** Previous and next guide IDs around the current one, without wrapping. */
export function neighbours(ids, current) {
  const at = ids.indexOf(current);
  if (at < 0) return { previous: null, next: null };
  return { previous: ids[at - 1] ?? null, next: ids[at + 1] ?? null };
}

/** The guide named by a URL's hash, and the search text and button filter from its query. */
export function parseLocation(href, guides) {
  const url = new URL(href, "https://example.invalid/");
  let id = "";
  try {
    id = decodeURIComponent(url.hash.replace(/^#/, ""));
  } catch {
    id = "";
  }
  const button = url.searchParams.get("button") || "";
  return {
    id: guides.some((guide) => guide.id === id) ? id : null,
    query: url.searchParams.get("q") || "",
    button: ["bottom", "middle", "top"].includes(button) ? button : "",
  };
}

/** 17.4 → "0:17". */
export function formatDuration(seconds) {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}
