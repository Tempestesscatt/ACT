
const menuButton = document.querySelector(".menu-button");
const mobilePanel = document.querySelector(".mobile-panel");

if (menuButton && mobilePanel) {
  menuButton.addEventListener("click", () => {
    const open = mobilePanel.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("menu-open", open);
  });
  mobilePanel.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      mobilePanel.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
      document.body.classList.remove("menu-open");
    });
  });
}

const current = document.body.dataset.page;
document.querySelectorAll(`[data-nav="${current}"]`).forEach(link => {
  link.setAttribute("aria-current", "page");
});

const form = document.querySelector("[data-demo-form]");
const status = document.querySelector(".form-status");
if (form && status) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    status.style.display = "block";
    status.textContent = "El formulari encara no està connectat. Abans de publicar-lo, cal definir el correu o servei que rebrà les sol·licituds.";
  });
}
