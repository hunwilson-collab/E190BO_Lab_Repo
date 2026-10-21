// The idea board page. Everything it knows comes from the API in main.py,
// fetched with relative URLs so it works in the codespace and on Railway.

const list = document.querySelector("#ideas");
const listStatus = document.querySelector("#list-status");
const countStatus = document.querySelector("#count");
const searchBox = document.querySelector("#search");
const sortMenu = document.querySelector("#sort");
const voterBox = document.querySelector("#voter");
const form = document.querySelector("#add-form");
const titleBox = document.querySelector("#title");
const bodyBox = document.querySelector("#body");
const addButton = document.querySelector("#add-button");
const addStatus = document.querySelector("#add-status");
const themeToggle = document.querySelector("#theme-toggle");

// The last list the server sent. Search and sort redraw from this, so they
// never make a request of their own.
let ideas = [];

// ── Local Storage, which can be blocked (private windows), so never trust it ──

function remember(key, value) {
  try { localStorage.setItem(key, value); } catch { /* fine: just not remembered */ }
}

function recall(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

// ── Talking to the API ────────────────────────────────────────────────────────

// fetch only rejects when there's no response at all. A 404 or 500 is still a
// response, so this turns a non-2xx status into an error too, with words a
// person can act on.
async function request(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Couldn't reach the server. Check your connection, then try again.");
  }
  if (!response.ok) {
    throw new Error(`The server had a problem (error ${response.status}). Try again in a moment.`);
  }
  return response.json();
}

function postJSON(url, data) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ── Loading the list ──────────────────────────────────────────────────────────

async function loadIdeas() {
  list.setAttribute("aria-busy", "true");
  listStatus.className = "";
  listStatus.textContent = "Loading ideas…";
  try {
    ideas = await request("/ideas");
    listStatus.textContent = "";
    render();
  } catch (err) {
    showListError(err.message);
  } finally {
    list.setAttribute("aria-busy", "false");
  }
}

function showListError(message) {
  listStatus.className = "error";
  listStatus.textContent = `Couldn't load the ideas. ${message} `;
  const retry = document.createElement("button");
  retry.type = "button";
  retry.textContent = "Try again";
  retry.addEventListener("click", loadIdeas);
  listStatus.append(retry);
}

// ── Drawing the list: search, sort, and the spotlight ─────────────────────────

const sorters = {
  votes: (a, b) => b.vote_count - a.vote_count || b.id - a.id,
  newest: (a, b) => b.id - a.id,          // ids only go up, so bigger is newer
  title: (a, b) => a.title.localeCompare(b.title),
};

function render() {
  const query = searchBox.value.trim().toLowerCase();
  const shown = ideas
    .filter((idea) => `${idea.title} ${idea.body ?? ""}`.toLowerCase().includes(query))
    .sort(sorters[sortMenu.value]);

  // The leader is decided across the whole board, not just what's showing.
  // Every idea tied for the most votes shares the label, and an all-zero
  // board has no leader at all.
  const most = Math.max(0, ...ideas.map((idea) => idea.vote_count));

  list.replaceChildren(...shown.map((idea) => ideaItem(idea, most > 0 && idea.vote_count === most)));

  if (ideas.length === 0) {
    countStatus.textContent = "No ideas yet. Add the first one above.";
  } else if (shown.length === 0) {
    countStatus.textContent = `No ideas match “${searchBox.value.trim()}”. ${ideas.length} on the board; clear the search to see them.`;
  } else {
    countStatus.textContent = `Showing ${shown.length} of ${ideas.length} ideas.`;
  }
}

function ideaItem(idea, isTop) {
  const li = document.createElement("li");
  li.className = "idea";
  li.classList.toggle("top", isTop);

  const text = document.createElement("div");
  text.className = "idea-text";
  if (isTop) {
    const label = document.createElement("span");
    label.className = "top-label";
    label.textContent = "Top idea";
    text.append(label);
  }
  const title = document.createElement("h3");
  title.textContent = idea.title;
  text.append(title);
  if (idea.body) {
    const body = document.createElement("p");
    body.textContent = idea.body;
    text.append(body);
  }
  const votes = document.createElement("p");
  votes.className = "hint";
  votes.textContent = idea.vote_count === 1 ? "1 vote" : `${idea.vote_count} votes`;
  text.append(votes);

  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Vote";
  button.setAttribute("aria-label", `Vote for ${idea.title}`);
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  status.className = "error";
  button.addEventListener("click", () => vote(idea, button, status));
  text.append(status);

  li.append(text, button);
  return li;
}

// ── Voting ────────────────────────────────────────────────────────────────────

async function vote(idea, button, status) {
  const voter = voterBox.value.trim();
  if (!voter) {
    status.textContent = "Type your name in “Your name, for voting” first.";
    voterBox.focus();
    return;
  }
  remember("voter", voter);
  button.disabled = true;
  button.textContent = "Voting…";
  status.textContent = "";
  try {
    await postJSON(`/ideas/${idea.id}/vote`, { voter });
    await loadIdeas();                     // fresh counts, and maybe a new leader
  } catch (err) {
    status.textContent = `Your vote didn't count. ${err.message}`;
    button.disabled = false;
    button.textContent = "Vote";
  }
}

// ── Adding an idea ────────────────────────────────────────────────────────────

form.addEventListener("submit", async (event) => {
  event.preventDefault();                  // stay on this page
  const title = titleBox.value.trim();
  if (!title) {
    addStatus.className = "error";
    addStatus.textContent = "Give your idea a title first.";
    titleBox.focus();
    return;
  }
  addButton.disabled = true;
  addStatus.className = "";
  addStatus.textContent = "Adding…";
  try {
    await postJSON("/ideas", { title, body: bodyBox.value.trim() });
    form.reset();                          // only on success: a failed add keeps the text
    addStatus.textContent = `Added “${title}”.`;
    await loadIdeas();
  } catch (err) {
    addStatus.className = "error";
    addStatus.textContent = `Couldn't add your idea. ${err.message} Your text is still here.`;
  } finally {
    addButton.disabled = false;
  }
});

// ── Light and dark theme ──────────────────────────────────────────────────────

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
}

themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  remember("theme", next);
});

// Until someone picks, follow the system's own setting.
applyTheme(recall("theme") ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

// ── Start ─────────────────────────────────────────────────────────────────────

voterBox.value = recall("voter") ?? "";
searchBox.addEventListener("input", render);
sortMenu.addEventListener("change", render);
loadIdeas();
