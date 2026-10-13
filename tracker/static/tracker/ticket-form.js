const form = document.querySelector("[data-ticket-form]");
const typeSelect = form.querySelector("[name=type]");
const bugFields = form.querySelectorAll("[data-bug-field]");

function updateBugFields() {
  const show = typeSelect.value === "bug";
  for (const field of bugFields) {
    field.hidden = !show;
  }
}

typeSelect.addEventListener("change", updateBugFields);
updateBugFields();

const suggestionsUrl = form.dataset.suggestionsUrl;
if (suggestionsUrl) {
  const titleInput = form.querySelector("[name=title]");
  const suggestions = form.querySelector("[data-ticket-suggestions]");
  const list = suggestions.querySelector("ul");
  let timer;
  let controller;

  titleInput.addEventListener("input", () => {
    clearTimeout(timer);
    if (controller) controller.abort();
    suggestions.hidden = true;
    const query = titleInput.value.trim();
    if (query.length < 3) return;
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const url = new URL(suggestionsUrl, window.location.origin);
        url.searchParams.set("q", query);
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) return;
        const tickets = await response.json();
        if (titleInput.value.trim() !== query) return;
        list.replaceChildren();
        for (const ticket of tickets) {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = ticket.url;
          link.textContent = `#${ticket.id} ${ticket.title}`;
          const status = document.createElement("span");
          status.textContent = ticket.status;
          item.append(link, status);
          list.append(item);
        }
        suggestions.hidden = tickets.length === 0;
      } catch (error) {
        if (error.name !== "AbortError") suggestions.hidden = true;
      }
    }, 400);
  });
}
