"""Lab 6 self-check: does your API still keep its contract, is your page
built right, and is your Dockerfile filled in?

Two terminals, both in src/:

    terminal 1:  uvicorn main:app --reload
    terminal 2:  python check.py

It has three parts. The API checks are Lab 5's: they send real requests to
your running server and compare the answers with CONTRACT.md. The page checks
fetch your page at / and read its HTML as the server sends it, before any
JavaScript runs: they can see its structure, not what your script draws later
or whether your error states work. The Dockerfile checks read the two files at
the top of your repo, and are skipped until you've added them.

It never imports your code. Every FAIL says what to look at. Fix the first FAIL
first: later checks often fail because of an earlier one.

To check your deployed app:  API_URL=https://your-app.up.railway.app python check.py
"""
import os
import re
import subprocess
import sys
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

BASE = os.environ.get("API_URL", "http://localhost:8000")
# A fresh connection for every request: a server that just crashed (a 500)
# closes its connection, and reusing it would crash this script instead.
api = httpx.Client(base_url=BASE, timeout=10,
                   limits=httpx.Limits(max_keepalive_connections=0))
tag = uuid.uuid4().hex[:6]      # so each run's test ideas get new titles
failures = 0
skipped = []


def check(what, ok, hint=""):
    """Print one PASS or FAIL line. On a FAIL, also say what to look at."""
    global failures
    if ok:
        print("PASS", what)
    else:
        failures += 1
        print("FAIL", what)
        if hint:
            print("    ", hint)


def skip(what, why):
    """Print one SKIP line: a check that can't run yet, which isn't a FAIL."""
    skipped.append(what)
    print("SKIP", what)
    print("    ", why)


def body(r):
    """The JSON a response sent back, or None if it didn't send any."""
    try:
        return r.json()
    except ValueError:
        return None


def id_of(r):
    """The id in a response like {"id": 3, ...}, or None."""
    b = body(r)
    return b.get("id") if isinstance(b, dict) else None


def listed(idea_id):
    """This idea's entry in GET /ideas, or None if it isn't there."""
    ideas = body(api.get("/ideas"))
    for i in ideas if isinstance(ideas, list) else []:
        if isinstance(i, dict) and i.get("id") == idea_id:
            return i
    return None


def crashed(r):
    """A hint for a 500, which always means the server's code raised an error."""
    if r.status_code == 500:
        return "got 500: your code crashed. The error is at the bottom of terminal 1."
    return ""


def why_not_422(r):
    """A hint for a bad request that wasn't rejected with a 422."""
    if r.status_code == 500:
        return ("got 500: a SQLModel class with table=True skips validation, so the bad "
                "body reached your database. Give the request body its own non-table "
                "class (the ⚠️ box in the handout).")
    if r.status_code < 300:
        return f"got {r.status_code}: you saved it anyway. Bad input should be refused."
    if r.status_code == 404:
        return "got 404: is this route there yet?"
    return f"got {r.status_code}."


try:
    api.get("/ideas")
except httpx.ConnectError:
    sys.exit(f"Can't reach your server at {BASE}.\n"
             "Start it in another terminal first:  uvicorn main:app --reload")

r = api.get("/ideas")
if r.status_code == 404 and "text/html" in api.get("/").headers.get("content-type", ""):
    sys.exit(f"Your server at {BASE} serves the page at / but GET /ideas is a 404.\n"
             "The StaticFiles mount is probably above your API routes. A mount at \"/\"\n"
             "matches every path, so it has to be the LAST thing in main.py.")


print("The API: Lab 5's contract, which your page relies on. These have to pass.\n")

r = api.get("/ideas")
check("GET /ideas answers 200", r.status_code == 200,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §1.")
check("GET /ideas is a JSON list", isinstance(body(r), list),
      "see above." if r.status_code != 200 else
      'a list, not wrapped in an object like {"ideas": [...]}. See CONTRACT.md §1.')

title = f"Test idea {tag}"
r = api.post("/ideas", json={"title": title, "body": "from check.py"})
new_id = id_of(r)
check("POST /ideas succeeds", r.status_code < 300,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §2.")
check("POST /ideas returns the new idea's id", new_id is not None,
      "return the saved idea, with the id the database picked.")
check("POST /ideas returns the title you sent",
      isinstance(body(r), dict) and body(r).get("title") == title)

entry = listed(new_id)
check("the new idea is in GET /ideas", entry is not None,
      "Not committed? Or a plain JOIN against votes, which drops an idea with no "
      "votes: that's what LEFT JOIN is for.")
second_id = id_of(api.post("/ideas", json={"title": f"Another test idea {tag}"}))
ideas = body(api.get("/ideas"))
check("a second new idea is listed too", listed(second_id) is not None,
      "Only one idea came back at all: a COUNT without a GROUP BY collapses every "
      "row into one." if isinstance(ideas, list) and len(ideas) == 1 else "")
check("listed ideas have a whole-number vote_count",
      entry is not None and type(entry.get("vote_count")) is int,
      "every idea in GET /ideas needs a vote_count. See CONTRACT.md §1.")
check("a new idea is listed with vote_count 0",
      entry is not None and entry.get("vote_count") == 0,
      "no vote_count yet: see above." if entry is None or "vote_count" not in entry else
      "COUNT(*) after a LEFT JOIN counts the one row of NULLs the join made for "
      "it. Count a column from the vote table instead.")

r = api.get(f"/ideas/{new_id}")
one = body(r)
check("GET /ideas/{id} answers 200 with that idea",
      r.status_code == 200 and isinstance(one, dict) and one.get("title") == title,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §3.")
check("GET /ideas/{id} includes a votes list",
      isinstance(one, dict) and isinstance(one.get("votes"), list),
      "a `votes` key holding a JSON list, empty if nobody has voted. See CONTRACT.md §3.")

r = api.post(f"/ideas/{new_id}/vote", json={"voter": f"ada-{tag}"})
api.post(f"/ideas/{new_id}/vote", json={"voter": f"grace-{tag}"})
voted = r.status_code < 300
check("POST /ideas/{id}/vote succeeds", voted,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §4.")
one = body(api.get(f"/ideas/{new_id}"))
votes = one.get("votes") if isinstance(one, dict) else None
check("after two votes, its votes list has two",
      isinstance(votes, list) and len(votes) == 2,
      "voting doesn't work yet: see above." if not voted else
      "no votes list yet: see above." if not isinstance(votes, list) else
      f"it has {len(votes)}. The votes were saved but aren't all coming back: check "
      "the join on idea_id.")
entry = listed(new_id)
count = entry.get("vote_count") if entry else None
check("after two votes, its vote_count is 2", count == 2,
      "voting doesn't work yet: see above." if not voted else
      "no vote_count yet: see above." if count is None else
      f"got {count!r}. The total for every idea? Your count is missing a GROUP BY. "
      "Stuck at 0? Check the join matches votes to their idea.")


print("\nThe API: good behaviour, as in Lab 5.\n")

r = api.post("/ideas", json={"title": f"Status {tag}"})
check("POST /ideas answers 201 Created", r.status_code == 201,
      f"got {r.status_code}. 201 is the honest answer when you made something: "
      "@app.post('/ideas', status_code=201)")
r2 = api.post("/ideas", json={"title": f"Second {tag}"})
check("two new ideas get different ids", None not in (id_of(r), id_of(r2))
      and id_of(r) != id_of(r2))

r = api.get("/ideas/99999999")
check("GET /ideas/{id} for a missing idea answers 404", r.status_code == 404,
      f"got {r.status_code}. An id that isn't there is a 404: not a 500, and not an "
      "empty 200.")
r = api.post("/ideas/99999999/vote", json={"voter": f"ghost-{tag}"})
check("voting on a missing idea answers 404", r.status_code == 404,
      f"got {r.status_code}. Check the idea exists before you save the vote.")

r = api.post("/ideas", json={"body": "no title here"})
check("POST /ideas with no title answers 422", r.status_code == 422, why_not_422(r))
r = api.post("/ideas", json={"title": {"not": "text"}})
check("POST /ideas with a title that isn't text answers 422", r.status_code == 422,
      why_not_422(r))
r = api.post(f"/ideas/{new_id}/vote", json={})
check("a vote with no voter answers 422", r.status_code == 422, why_not_422(r))
r = api.post(f"/ideas/{new_id}/vote", json={"voter": {"not": "text"}})
check("a vote whose voter isn't text answers 422", r.status_code == 422, why_not_422(r))



# ── The page ──────────────────────────────────────────────────────────────────

CONTROLS = {"input", "select", "textarea"}
UNLABELLED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
INTERACTIVE = {"a", "button", "input", "select", "textarea", "summary", "label"}
HOST = re.compile(r"localhost|127\.0\.0\.1|0\.0\.0\.0|\.app\.github\.dev|:8000\b")
# A host only matters inside a JavaScript string; one in a comment is harmless.
# So drop comments (a // after a space or at the start of a line, never the //
# in "https://"), then look inside each string.
COMMENT = re.compile(r"/\*.*?\*/|(?:^|(?<=\s))//[^\n]*", re.S | re.M)
STRING = re.compile(r"""(["'`])((?:\\.|(?!\1).)*)\1""")


class Page(HTMLParser):
    """Just enough of the page's structure to check it."""

    def __init__(self):
        super().__init__()
        self.stack = []        # open tags, so we know what a control sits inside
        self.elements = []     # (tag, attrs, inside a <label>?)
        self.headings = []     # heading levels, in order
        self.label_for = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs, "label" in self.stack))
        if tag == "label" and attrs.get("for"):
            self.label_for.add(attrs["for"])
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag not in {"meta", "link", "input", "img", "br", "hr", "source"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def all(self, tag):
        return [(a, in_label) for t, a, in_label in self.elements if t == tag]


print("\nThe page: what its HTML says, before any JavaScript runs.\n")

r = api.get("/")
served = r.status_code == 200 and "text/html" in r.headers.get("content-type", "")
check("GET / serves your page", served,
      f"got {r.status_code} ({r.headers.get('content-type')}). Serve web/ from this "
      'server, as the LAST line of main.py:  app.mount("/", StaticFiles(directory="web", '
      'html=True), name="web")  and make sure web/index.html exists.')

if not served:
    skip("the other page checks", "there's no page to check yet: see the FAIL above.")
else:
    page = Page()
    page.feed(r.text)
    here = urlparse(str(r.url)).netloc

    def local(url):
        return urlparse(urljoin(str(r.url), url)).netloc == here

    scripts = [a["src"] for a, _ in page.all("script") if a.get("src")]
    styles = [a["href"] for a, _ in page.all("link")
              if "stylesheet" in (a.get("rel") or "") and a.get("href")]
    missing = [u for u in scripts + styles
               if local(u) and api.get(urljoin(str(r.url), u)).status_code != 200]
    check("the page loads a script, and its own scripts and styles load",
          scripts and not missing,
          'no <script src="..."> at all, so it can\'t talk to your API.' if not scripts else
          f"the server returns an error for {missing}. Paths are relative to web/: "
          '<script src="app.js"> means web/app.js.')

    hosts = []
    for src in scripts:
        if local(src):
            js = COMMENT.sub("", api.get(urljoin(str(r.url), src)).text)
            hosts += [f"{src}: {m.group(0)[:50]}" for m in STRING.finditer(js)
                      if HOST.search(m.group(2))]
    check("your JavaScript doesn't name a host", not hosts,
          f"{', '.join(hosts[:3])}. That breaks as soon as the app moves, and it does when "
          'you deploy it. The page and the API share a server, so fetch("/ideas") is enough.')

    html = page.all("html")
    check("<html> says what language the page is in", bool(html and html[0][0].get("lang")),
          'e.g. <html lang="en">. Screen readers use it to pick a voice.')

    viewport = [a for a, _ in page.all("meta") if a.get("name") == "viewport"]
    check("there's a viewport tag, for phones",
          bool(viewport) and "width=device-width" in viewport[0].get("content", ""),
          'without one a phone shows a shrunken desktop page. In <head>:  '
          '<meta name="viewport" content="width=device-width, initial-scale=1">')

    h1s = page.headings.count(1)
    check("there's exactly one <h1>", h1s == 1,
          f"there are {h1s}. One <h1>, naming the page, is where a screen reader starts. "
          "Two? Look for conflict markers left from a merge.")
    jumps = [(a, b) for a, b in zip(page.headings, page.headings[1:]) if b > a + 1]
    check("headings don't skip a level", not jumps,
          f"h{jumps[0][0]} goes straight to h{jumps[0][1]}. Headings are an outline, not a "
          "font size: for smaller text, use CSS." if jumps else "")

    unlabelled = []
    for tag in CONTROLS:
        for attrs, in_label in page.all(tag):
            if tag == "input" and attrs.get("type", "text") in UNLABELLED_INPUT_TYPES:
                continue
            if not (in_label or attrs.get("id") in page.label_for
                    or attrs.get("aria-label") or attrs.get("aria-labelledby")):
                name = attrs.get("id") or attrs.get("name") or attrs.get("placeholder") or "?"
                unlabelled.append(f"<{tag}> {name!r}")
    check("every form control has a label", not unlabelled,
          f"no label: {', '.join(unlabelled)}. A placeholder isn't a label. "
          'Use <label for="the-id">...</label>.')

    fake = [f"<{t}>" for t, a, _ in page.elements if "onclick" in a and t not in INTERACTIVE]
    check("only buttons and links are clickable", not fake,
          f"{', '.join(fake)} with an onclick: a keyboard can't reach it. If it does "
          "something, make it a <button>; if it goes somewhere, an <a href>.")

    no_alt = [a.get("src", "?") for a, _ in page.all("img") if "alt" not in a]
    check("every image has alt text", not no_alt,
          f"{no_alt}: describe what it shows, or alt=\"\" if it's decoration.")

    check("there's a <form> to add an idea", bool(page.all("form")),
          "a <form> is what makes Enter submit, and tells assistive technology the "
          "inputs belong together. Handle its submit event, and call event.preventDefault().")


# ── The Dockerfile ────────────────────────────────────────────────────────────

print("\nThe Dockerfile: the two files at the top of your repo.\n")


def repo_root():
    here = Path(__file__).resolve().parent
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here,
                             capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return here.parent


root = repo_root()
dockerfile = root / "Dockerfile"
if not dockerfile.is_file():
    skip("the Dockerfile checks", f"there's no Dockerfile at the top of your repo ({root}) "
         "yet. That's the handout's last part, Put it on the internet.")
else:
    lines = [l for l in dockerfile.read_text().splitlines() if not l.lstrip().startswith("#")]
    text = "\n".join(lines)
    blanks = text.count("____")
    check("the Dockerfile has no blanks left", blanks == 0,
          f"{blanks} blank(s), ____, still to fill in.")
    base = re.search(r"^FROM\s+(\S+)", text, re.M)
    check("it starts from a Python 3.13 image",
          bool(base) and base.group(1).startswith("python:3.13"),
          f"FROM {base.group(1) if base else '?'}: use an official Python 3.13 image, "
          "the same Python as your codespace.")
    copies = re.findall(r"^COPY\s+(\S+)\s+\S+", text, re.M)
    check("it copies src/ into the image", any(c.rstrip("/") == "src" for c in copies),
          "the Dockerfile is at the top of your repo and your app is in src/, so that's "
          "the folder to COPY.")
    cmd = (re.findall(r"^CMD\s+(.*)$", text, re.M) or [""])[-1]
    check("the server listens on every interface (0.0.0.0)", "0.0.0.0" in cmd,
          "inside a container, 127.0.0.1 is the container itself, so nothing outside "
          "it can connect.")
    check("the server listens on the platform's port ($PORT)", "$PORT" in cmd or "${PORT}" in cmd,
          "a platform chooses the port and puts it in the PORT variable; a server on any "
          "other port can't be reached.")
    ignore = root / ".dockerignore"
    patterns = ignore.read_text().split() if ignore.is_file() else []
    check(".dockerignore keeps your database and secrets out",
          "**/*.db" in patterns and "**/.env" in patterns,
          "no .dockerignore at the top of your repo: use the one from the deploy kit."
          if not ignore.is_file() else
          "it needs **/*.db and **/.env, so app.db and any secrets in src/ stay out.")


print()
if failures:
    print(f"{failures} FAIL. Start with the first one.")
elif skipped:
    print(f"Everything that could run passes. Skipped: {', '.join(skipped)}.")
else:
    print("Everything passes.")
sys.exit(1 if failures else 0)
