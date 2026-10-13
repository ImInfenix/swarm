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
