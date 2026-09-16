/* ==============================================================
   CHANAKYA COMPETITION CRACKER — MCQ QUIZ ENGINE
   Reads question data from a JSON script tag (#mcq-data) and
   renders one question at a time with scoring at the end.
   ============================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const dataEl = document.getElementById("mcq-data");
  if (!dataEl) return;

  const mcqSet = JSON.parse(dataEl.textContent);
  const questions = mcqSet.questions || [];
  let current = 0;
  let selected = new Array(questions.length).fill(null);
  let answered = new Array(questions.length).fill(false);

  const questionCard = document.getElementById("mcq-question-card");
  const progressBar = document.getElementById("mcq-progress-bar");
  const progressLabel = document.getElementById("mcq-progress-label");
  const prevBtn = document.getElementById("mcq-prev-btn");
  const nextBtn = document.getElementById("mcq-next-btn");
  const resultPanel = document.getElementById("mcq-result-panel");
  const quizWrap = document.getElementById("mcq-quiz-wrap");

  const letters = ["A", "B", "C", "D", "E", "F"];

  function renderQuestion() {
    const q = questions[current];
    progressBar.style.width = (((current) / questions.length) * 100) + "%";
    progressLabel.textContent = "Question " + (current + 1) + " of " + questions.length;

    let optionsHtml = "";
    q.options.forEach(function (opt, i) {
      let cls = "mcq-option";
      if (answered[current]) {
        if (i === q.answer) cls += " correct";
        else if (i === selected[current] && i !== q.answer) cls += " incorrect";
      } else if (selected[current] === i) {
        cls += " selected";
      }
      optionsHtml +=
        '<div class="' + cls + '" data-index="' + i + '">' +
          '<span class="mcq-option-letter">' + letters[i] + '</span>' +
          '<span>' + escapeHtml(opt) + '</span>' +
        '</div>';
    });

    let explanationHtml = "";
    if (answered[current] && q.explanation) {
      explanationHtml =
        '<div class="mcq-explanation" style="display:block">' +
          '<strong>Explanation: </strong>' + escapeHtml(q.explanation) +
        '</div>';
    }

    questionCard.innerHTML =
      '<div class="eyebrow">' + escapeHtml(mcqSet.category || "") + '</div>' +
      '<h3 style="margin: 10px 0 20px;">' + escapeHtml(q.q) + '</h3>' +
      '<div class="mcq-options">' + optionsHtml + '</div>' +
      explanationHtml;

    prevBtn.disabled = current === 0;
    nextBtn.textContent = current === questions.length - 1 ? "Finish" : "Next";
    nextBtn.disabled = selected[current] === null;

    questionCard.querySelectorAll(".mcq-option").forEach(function (el) {
      el.addEventListener("click", function () {
        if (answered[current]) return;
        selected[current] = parseInt(el.dataset.index, 10);
        answered[current] = true;
        renderQuestion();
      });
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  prevBtn.addEventListener("click", function () {
    if (current > 0) { current--; renderQuestion(); }
  });

  nextBtn.addEventListener("click", function () {
    if (current < questions.length - 1) {
      current++;
      renderQuestion();
    } else {
      showResults();
    }
  });

  function showResults() {
    let score = 0;
    questions.forEach(function (q, i) {
      if (selected[i] === q.answer) score++;
    });
    const pct = Math.round((score / questions.length) * 100);

    quizWrap.style.display = "none";
    resultPanel.style.display = "block";
    resultPanel.innerHTML =
      '<div class="mcq-result-score">' + score + ' / ' + questions.length + '</div>' +
      '<p style="margin-top:10px;">You scored ' + pct + '% on this set.</p>' +
      '<div style="margin-top:28px; display:flex; gap:14px; justify-content:center;">' +
        '<button class="btn btn-outline" id="mcq-retry-btn">Retry this set</button>' +
        '<a class="btn btn-gold" href="/mcqs">Browse more sets</a>' +
      '</div>';

    document.getElementById("mcq-retry-btn").addEventListener("click", function () {
      current = 0;
      selected = new Array(questions.length).fill(null);
      answered = new Array(questions.length).fill(false);
      quizWrap.style.display = "block";
      resultPanel.style.display = "none";
      renderQuestion();
    });
  }

  renderQuestion();
});
