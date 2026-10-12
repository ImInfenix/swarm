const passwordButton = document.getElementById("password-toggle");
const passwordPanel = document.getElementById("password-panel");

passwordButton.addEventListener("click", () => {
  const expanded = passwordButton.getAttribute("aria-expanded") === "true";
  passwordButton.setAttribute("aria-expanded", String(!expanded));
  passwordPanel.hidden = expanded;
  if (!expanded) {
    passwordPanel.querySelector("input")?.focus();
  }
});

for (const [name, dialogId] of [["logout-all", "logout-all-dialog"], ["delete-account", "delete-account-dialog"]]) {
  const dialog = document.getElementById(dialogId);
  document.querySelector(`[data-open-${name}]`).addEventListener("click", () => dialog.showModal());
  document.querySelector(`[data-close-${name}]`).addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
}
