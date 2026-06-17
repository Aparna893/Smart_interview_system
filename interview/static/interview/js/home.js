/* ===================================================== */
/* QUESTION SLIDER NAVIGATION  (questions.html)        */
/* ===================================================== */

function nextQuestion(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    const questions = slider.querySelectorAll('.single-question');
    let current = -1;
    questions.forEach((q, i) => { if (q.style.display === 'block') current = i; });
    if (current < questions.length - 1) {
        questions[current].style.display = 'none';
        questions[current + 1].style.display = 'block';
    }
}

function previousQuestion(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    const questions = slider.querySelectorAll('.single-question');
    let current = -1;
    questions.forEach((q, i) => { if (q.style.display === 'block') current = i; });
    if (current > 0) {
        questions[current].style.display = 'none';
        questions[current - 1].style.display = 'block';
    }
}

/* ===================================================== */
/* CSRF COOKIE HELPER                                    */
/* ===================================================== */

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

/* ===================================================== */
/* CHECKBOX VALIDATION + COUNTER  (questions.html)      */
/* ===================================================== */

function attachCheckboxValidation(maxQuestions) {
    const checkboxes = document.querySelectorAll('.question-checkbox');
    const counter    = document.getElementById('selectionCounter');

    function updateCounter() {
        const checked = document.querySelectorAll('.question-checkbox:checked').length;
        if (counter) {
            counter.textContent = `${checked} / ${maxQuestions} selected`;
            counter.style.color = checked === maxQuestions
                ? 'var(--green)'
                : 'var(--blue)';
        }
    }

    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            if (!cb.checked) { updateCounter(); return; }
            const alreadyChecked = document.querySelectorAll('.question-checkbox:checked').length;
            if (alreadyChecked > maxQuestions) {
                cb.checked = false;
                alert(`You can only select ${maxQuestions} questions. Uncheck one before selecting another.`);
            }
            updateCounter();
        });
    });

    updateCounter();
}

/* ===================================================== */
/* FORM SUBMIT VALIDATION                                */
/* ===================================================== */

function attachFormValidation(maxQuestions) {
    const form = document.getElementById('questionsForm');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        const checked = document.querySelectorAll('.question-checkbox:checked').length;
        if (checked === 0) {
            e.preventDefault();
            alert('Please select at least 1 question before finalizing.');
            return;
        }
        if (checked > maxQuestions) {
            e.preventDefault();
            alert(`You selected ${checked} questions but the limit is ${maxQuestions}. Please uncheck ${checked - maxQuestions} question(s).`);
        }
    });
}

/* ===================================================== */
/* DOM READY                                             */
/* ===================================================== */

document.addEventListener('DOMContentLoaded', function () {
    const maxInput    = document.getElementById('maxQuestions');
    const maxQuestions = Number(maxInput ? maxInput.value : 10) || 10;

    attachCheckboxValidation(maxQuestions);
    attachFormValidation(maxQuestions);

    // Generate button (used on older question pages if still present)
    const genBtn = document.getElementById('generateBtn');
    if (!genBtn) return;

    genBtn.addEventListener('click', async function () {
        const interviewId   = this.dataset.interviewId;
        const spinner       = document.getElementById('generateSpinner');
        const providerLabel = document.getElementById('providerLabel');

        if (spinner)      spinner.style.display = 'inline';
        genBtn.disabled = true;

        try {
            const resp = await fetch('/generate_questions_ajax/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || ''
                },
                body: JSON.stringify({
                    interview_id:  interviewId,
                    max_questions: maxQuestions
                })
            });

            const data = await resp.json();

            if (data.status !== 'success') {
                alert('Error generating questions: ' + (data.message || 'unknown'));
                genBtn.disabled = false;
                if (spinner) spinner.style.display = 'none';
                return;
            }

            if (providerLabel) providerLabel.textContent = data.provider || 'OpenRouter';
            window.location.href = `/questions/${interviewId}/`;

        } catch (err) {
            console.error(err);
            alert('Failed to generate questions');
            genBtn.disabled = false;
        } finally {
            if (spinner) spinner.style.display = 'none';
        }
    });
});
