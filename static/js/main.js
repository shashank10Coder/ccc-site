/* ==============================================================
   CHANAKYA COMPETITION CRACKER — GENERAL SITE BEHAVIOUR
   ============================================================== */

document.addEventListener("DOMContentLoaded", function () {

  // ---------- Mobile sidebar toggle ----------
  const menuToggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
    document.addEventListener("click", function (e) {
      if (
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        !menuToggle.contains(e.target)
      ) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ---------- Auto-dismiss flash messages ----------
  document.querySelectorAll(".flash-msg").forEach(function (msg, i) {
    setTimeout(function () {
      msg.style.opacity = "0";
      msg.style.transform = "translateX(16px)";
      setTimeout(function () { msg.remove(); }, 300);
    }, 4500 + i * 300);
  });

  // ---------- OTP input auto-advance ----------
  const otpInputs = document.querySelectorAll(".otp-input-row input");
  if (otpInputs.length) {
    otpInputs.forEach(function (input, index) {
      input.addEventListener("input", function () {
        input.value = input.value.replace(/[^0-9]/g, "").slice(0, 1);
        if (input.value && otpInputs[index + 1]) {
          otpInputs[index + 1].focus();
        }
        updateOtpHiddenField();
      });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Backspace" && !input.value && otpInputs[index - 1]) {
          otpInputs[index - 1].focus();
        }
      });
      input.addEventListener("paste", function (e) {
        e.preventDefault();
        const pasted = (e.clipboardData.getData("text") || "").replace(/[^0-9]/g, "").slice(0, otpInputs.length);
        pasted.split("").forEach(function (digit, i) {
          if (otpInputs[i]) otpInputs[i].value = digit;
        });
        updateOtpHiddenField();
        if (otpInputs[pasted.length]) otpInputs[pasted.length].focus();
      });
    });
    function updateOtpHiddenField() {
      const hidden = document.getElementById("otp-combined");
      if (hidden) {
        hidden.value = Array.from(otpInputs).map(function (i) { return i.value; }).join("");
      }
    }
    otpInputs[0].focus();
  }

  // ---------- Resend OTP button ----------
  const resendBtn = document.getElementById("resend-otp-btn");
  if (resendBtn) {
    let cooldown = 0;
    resendBtn.addEventListener("click", function () {
      if (cooldown > 0) return;
      fetch("/resend-otp", { method: "POST" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          const statusEl = document.getElementById("otp-resend-status");
          if (statusEl) statusEl.textContent = data.message;
          cooldown = 30;
          resendBtn.disabled = true;
          const timer = setInterval(function () {
            cooldown--;
            resendBtn.textContent = "Resend code (" + cooldown + "s)";
            if (cooldown <= 0) {
              clearInterval(timer);
              resendBtn.disabled = false;
              resendBtn.textContent = "Resend code";
            }
          }, 1000);
        });
    });
  }

  // ---------- Profile picture live preview ----------
  const picInput = document.getElementById("profile-pic-input");
  const picPreview = document.getElementById("profile-pic-preview");
  if (picInput && picPreview) {
    picInput.addEventListener("change", function () {
      if (picInput.files && picInput.files[0]) {
        picPreview.src = URL.createObjectURL(picInput.files[0]);
      }
    });
  }

  // ---------- Admin: dynamic MCQ question builder ----------
  const addQuestionBtn = document.getElementById("add-question-btn");
  const questionsContainer = document.getElementById("questions-container");
  if (addQuestionBtn && questionsContainer) {
    addQuestionBtn.addEventListener("click", function () {
      const row = document.createElement("div");
      row.className = "mcq-builder-row";
      row.innerHTML =
        '<div class="form-group">' +
          '<label>Question text</label>' +
          '<input type="text" name="question_text[]" required>' +
        '</div>' +
        '<div class="form-group">' +
          '<label>Options (comma separated, e.g. Delhi, Mumbai, Chennai, Kolkata)</label>' +
          '<input type="text" name="question_options[]" required>' +
        '</div>' +
        '<div class="form-grid">' +
          '<div class="form-group">' +
            '<label>Correct option number (0 = first option, 1 = second...)</label>' +
            '<input type="number" name="question_answer[]" min="0" value="0" required>' +
          '</div>' +
          '<div class="form-group">' +
            '<label>Explanation (optional)</label>' +
            '<input type="text" name="question_explanation[]">' +
          '</div>' +
        '</div>' +
        '<button type="button" class="btn btn-ghost btn-sm remove-question-btn">Remove this question</button>';
      questionsContainer.appendChild(row);
    });

    questionsContainer.addEventListener("click", function (e) {
      if (e.target.classList.contains("remove-question-btn")) {
        e.target.closest(".mcq-builder-row").remove();
      }
    });
  }

  // ---------- "is_paid" checkbox toggles price field ----------
  document.querySelectorAll(".is-paid-toggle").forEach(function (checkbox) {
    const priceField = document.querySelector(checkbox.dataset.priceTarget);
    if (!priceField) return;
    function sync() {
      priceField.closest(".form-group").style.display = checkbox.checked ? "block" : "none";
    }
    checkbox.addEventListener("change", sync);
    sync();
  });
});


/* ==========================================================
   CCC LANGUAGE SELECTION - ADDED WITHOUT CHANGING EXISTING JS
   ========================================================== */
(function () {
  "use strict";

  function setTranslateCookie(language) {
    var value = language === "hi" ? "/en/hi" : "/en/en";
    document.cookie = "googtrans=" + value + "; path=/";
    document.cookie = "googtrans=" + value + "; path=/; SameSite=Lax";
  }

  function hideLanguageSelector() {
    var selector = document.getElementById("language-selector");
    if (selector) selector.classList.remove("is-visible");
  }

  function showLanguageSelector() {
    var selector = document.getElementById("language-selector");
    if (selector) selector.classList.add("is-visible");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var savedLanguage = localStorage.getItem("ccc_language");
    var selector = document.getElementById("language-selector");

    if (!savedLanguage) {
      showLanguageSelector();
    } else {
      hideLanguageSelector();
    }

    if (!selector) return;

    selector.querySelectorAll(".language-choice-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        var language = button.getAttribute("data-language");

        localStorage.setItem("ccc_language", language);
        setTranslateCookie(language);
        hideLanguageSelector();

        // Reload so the selected language is applied consistently to
        // the complete page and remains active across all site pages.
        window.location.reload();
      });
    });
  });
})();
