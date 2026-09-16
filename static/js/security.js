/* ==============================================================
   CHANAKYA COMPETITION CRACKER — CONTENT PROTECTION SCRIPT
   ==============================================================
   IMPORTANT HONESTY NOTE FOR THE SITE OWNER (read this):

   This script makes copying content and finding PDF files a bit
   harder for a casual visitor. It CANNOT:
     - Stop someone from taking a screenshot or screen-recording
       their own device. No website, anywhere, can do that -- the
       operating system controls that, not the browser.
     - Truly "close the browser tab" when DevTools opens. Browsers
       do not allow JavaScript to do this reliably, and modern
       browsers ignore/undo attempts at this. So instead, this
       script BLURS the page and shows a warning, which is the
       realistic version of that request.
     - Stop a technically determined person forever. It raises the
       effort required for casual copying, which is what most
       real-world content protection actually achieves.

   What this script DOES do:
     1. Disables right-click context menu site-wide.
     2. Disables text selection on protected content areas.
     3. Blocks common copy/save/print/view-source keyboard shortcuts.
     4. Detects when browser DevTools is opened (best-effort, not
        100% reliable across all browsers) and shows a warning
        overlay that blurs the page content.
     5. Disables dragging images/PDF embeds off the page.
   ============================================================== */

(function () {
  "use strict";

  // ---------- 1. Disable right-click menu ----------
  document.addEventListener("contextmenu", function (e) {
    e.preventDefault();
  });

  // ---------- 2. Disable text selection on protected areas ----------
  document.addEventListener("selectstart", function (e) {
    if (e.target.closest(".protected-content, .pdf-viewer-frame")) {
      e.preventDefault();
    }
  });

  // ---------- 3. Block common copy / save / devtools shortcuts ----------
  document.addEventListener("keydown", function (e) {
    const key = e.key ? e.key.toLowerCase() : "";
    const blockedCombos = [
      // Ctrl/Cmd + S (save page), P (print), U (view source), C (copy on protected area)
      (e.ctrlKey || e.metaKey) && key === "s",
      (e.ctrlKey || e.metaKey) && key === "p",
      (e.ctrlKey || e.metaKey) && key === "u",
      // DevTools shortcuts
      key === "f12",
      (e.ctrlKey || e.metaKey) && e.shiftKey && (key === "i" || key === "j" || key === "c"),
    ];
    if (blockedCombos.some(Boolean)) {
      e.preventDefault();
    }
  });

  // ---------- 4. Best-effort DevTools detection ----------
  // Technique: measure the gap between outer and inner window
  // dimensions. When DevTools docks inside the browser window,
  // this gap grows suddenly. This is a heuristic, not a guarantee.
  let devtoolsWarningShown = false;

  function showSecurityWarning() {
    if (devtoolsWarningShown) return;
    devtoolsWarningShown = true;
    const overlay = document.getElementById("security-overlay");
    if (overlay) overlay.classList.add("show");
  }

  function checkDevTools() {
    const threshold = 160;
    const widthGap = window.outerWidth - window.innerWidth;
    const heightGap = window.outerHeight - window.innerHeight;
    if (widthGap > threshold || heightGap > threshold) {
      showSecurityWarning();
    }
  }
  setInterval(checkDevTools, 1000);

  // ---------- 5. Disable dragging on images and embedded PDFs ----------
  document.addEventListener("dragstart", function (e) {
    if (e.target.tagName === "IMG" || e.target.closest(".pdf-viewer-frame")) {
      e.preventDefault();
    }
  });
})();
