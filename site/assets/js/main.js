// Progressive enhancement only: the site is fully usable without JavaScript.
(function () {
  "use strict";

  document.querySelectorAll("[data-slider]").forEach(function (slider) {
    var track = slider.querySelector("[data-slider-track]");
    var slides = slider.querySelectorAll("[data-slide]");
    var dots = slider.querySelectorAll("[data-slider-dot]");
    var caption = slider.querySelector("[data-slider-caption]");
    var prevBtn = slider.querySelector("[data-slider-prev]");
    var nextBtn = slider.querySelector("[data-slider-next]");
    if (!track || slides.length < 2) return;

    var current = 0;
    var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function setActive(index) {
      current = (index + slides.length) % slides.length;
      dots.forEach(function (dot, i) {
        var active = i === current;
        dot.classList.toggle("is-active", active);
        if (active) {
          dot.setAttribute("aria-current", "true");
        } else {
          dot.removeAttribute("aria-current");
        }
      });
      if (caption && slides[current]) {
        var figcap = slides[current].querySelector("figcaption");
        if (figcap) {
          caption.textContent = figcap.textContent;
        }
      }
    }

    function goTo(index, instant) {
      var targetIndex = (index + slides.length) % slides.length;
      setActive(targetIndex);
      if (instant || reducedMotion) {
        track.scrollLeft = targetIndex * track.clientWidth;
      } else {
        track.scrollTo({
          left: targetIndex * track.clientWidth,
          behavior: "smooth"
        });
      }
    }

    if (window.location.hash) {
      slides.forEach(function (slide, idx) {
        if ("#" + slide.id === window.location.hash) {
          goTo(idx, true);
        }
      });
    }

    if (prevBtn) {
      prevBtn.hidden = false;
      prevBtn.addEventListener("click", function () { goTo(current - 1); });
    }
    if (nextBtn) {
      nextBtn.hidden = false;
      nextBtn.addEventListener("click", function () { goTo(current + 1); });
    }

    dots.forEach(function (dot, idx) {
      dot.addEventListener("click", function (e) {
        e.preventDefault();
        goTo(idx);
      });
    });

    track.addEventListener("scroll", function () {
      if (!track.clientWidth) return;
      var idx = Math.round(track.scrollLeft / track.clientWidth);
      if (idx >= 0 && idx < slides.length && idx !== current) {
        setActive(idx);
      }
    }, { passive: true });

    slider.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(current - 1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goTo(current + 1);
      }
    });
  });

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

