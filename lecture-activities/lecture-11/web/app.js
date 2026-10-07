// The idea board's JavaScript. index.html loads it with defer, so it runs
// once, after the whole page has been parsed, and again only when something
// happens: a click, a submit, or a response arriving.
const list = document.querySelector("#ideas");
async function loadIdeas() {
 const response = await fetch("/ideas"); // GET /ideas, from this server
 const ideas = await response.json(); // the body, parsed from JSON
 list.replaceChildren(); // empty the list
 for (const idea of ideas) {
 const li = document.createElement("li");
 li.textContent = `${idea.title} (${idea.vote_count} votes)`;
 list.append(li);
 }
}
loadIdeas();
