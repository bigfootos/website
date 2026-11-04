// Progressive enhancement only: the site is fully usable without JavaScript.
(function () {
  "use strict";

  if (!navigator.clipboard) return;

  document.querySelectorAll("button.copy[data-copy]").forEach(function (button) {
    var target = document.getElementById(button.dataset.copy);
    if (!target) return;
    button.hidden = false;

    button.addEventListener("click", function () {
      navigator.clipboard.writeText(target.textContent.trim()).then(function () {
        button.textContent = "Copied";
        setTimeout(function () { button.textContent = "Copy"; }, 1800);
      });
    });
  });
})();
