for (const form of document.querySelectorAll("[data-ticket-filters]")) {
  const search = form.querySelector('input[name="q"]');
  const results = document.querySelector("[data-ticket-results]");
  let pending;
  let activeRequest;

  function scheduleFilter() {
    window.clearTimeout(pending);
    activeRequest?.abort();
    pending = window.setTimeout(() => form.requestSubmit(), 600);
  }

  search.addEventListener("input", (event) => {
    if (!event.isComposing) {
      scheduleFilter();
    }
  });
  search.addEventListener("compositionstart", () => {
    window.clearTimeout(pending);
    activeRequest?.abort();
  });
  search.addEventListener("compositionend", scheduleFilter);

  for (const select of form.querySelectorAll("select")) {
    select.addEventListener("change", () => {
      window.clearTimeout(pending);
      form.requestSubmit();
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    window.clearTimeout(pending);
    activeRequest?.abort();

    const controller = new AbortController();
    activeRequest = controller;
    const url = new URL(window.location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) {
        throw new Error("Could not load tickets");
      }
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const nextResults = page.querySelector("[data-ticket-results]");
      if (!nextResults) {
        throw new Error("Ticket results are missing");
      }
      if (controller.signal.aborted || activeRequest !== controller) {
        return;
      }
      results.replaceChildren(...nextResults.children);
      window.history.replaceState(window.history.state, "", url);
      const languageNext = document.querySelector('.language-switch [name="next"]');
      if (languageNext) {
        languageNext.value = url.pathname + url.search;
      }
    } catch {
      if (!controller.signal.aborted) {
        window.location.assign(url);
      }
    } finally {
      if (activeRequest === controller) {
        activeRequest = null;
      }
    }
  });
}
