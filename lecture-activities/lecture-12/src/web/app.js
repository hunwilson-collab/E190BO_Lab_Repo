const list = document.querySelector("#ideas");
const listStatus = document.querySelector("#list-status");

async function loadIdeas() {
  listStatus.textContent = "Loading ideas…";
  try {
    const response = await fetch("/ideas");
    if (!response.ok) {                       // a 404 or a 500 lands here
      throw new Error(`The server said ${response.status}.`);
    }
    const ideas = await response.json();
    list.replaceChildren();
    for (const idea of ideas) {
      const li = document.createElement("li");
      li.textContent = `${idea.title} (${idea.vote_count} votes)`;
      list.append(li);
    }
    listStatus.textContent = ideas.length ? "" : "No ideas yet.";
  } catch (err) {                             // ...and so does no response at all
    listStatus.textContent = `Couldn't load ideas. ${err.message} `;
    const retry = document.createElement("button");
    retry.textContent = "Try again";
    retry.addEventListener("click", loadIdeas);
    listStatus.append(retry);
  }
}

const form = document.querySelector("#add-form");
const addStatus = document.querySelector("#add-status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();                     // stay on this page
  const title = document.querySelector("#title").value;
  const response = await fetch("/ideas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title }),
  });
  if (response.ok) {
    form.reset();                             // a failed add keeps the text
    addStatus.textContent = "Added.";
    loadIdeas();
  } else {
    addStatus.textContent = `Couldn't add that. The server said ${response.status}.`;
  }
});

loadIdeas();
