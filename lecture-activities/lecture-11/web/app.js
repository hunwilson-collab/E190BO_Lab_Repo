// The idea board's JavaScript. index.html loads it with defer, so it runs
// once, after the whole page has been parsed, and again only when something
// happens: a click, a submit, or a response arriving.
const list = document.querySelector("#ideas");
const listStatus = document.querySelector("#list-status");

async function loadIdeas() {
listStatus.textContent = "Loading ideas…";
try {
const response = await fetch("/ideas");
// TODO 1: if the response isn't OK, throw an Error that says its status.

const ideas = await response.json();
list.replaceChildren();
for (const idea of ideas) {
const li = document.createElement("li");
li.textContent = `${idea.title} (${idea.vote_count} votes)`;
list.append(li);
}
listStatus.textContent = ideas.length ? "" : "No ideas yet.";
} catch (err) {
// TODO 2: put "Couldn't load ideas." and err.message in listStatus,
// then add a "Try again" button to it that calls loadIdeas when clicked.
}
}

loadIdeas();
const form = document.querySelector("#add-form");
const addStatus = document.querySelector("#add-status");
form.addEventListener("submit", async (event) => {
 event.preventDefault(); // stay on this page
 const title = document.querySelector("#title").value;
 const response = await fetch("/ideas", {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ title: title }),
 });
 if (response.ok) {
 form.reset(); // a failed add keeps the text
 addStatus.textContent = "Added.";
 loadIdeas();
 } else {
 addStatus.textContent = `Couldn't add that. The server said ${response.status}.`;
 }
});