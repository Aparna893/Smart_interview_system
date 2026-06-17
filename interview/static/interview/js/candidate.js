/* ===================================================== */
/* CANDIDATE INTERVIEW LOGIC */
/* ===================================================== */

// Variables are initialized in the HTML template:
// const questions, let currentQuestion, let answers,
// let recognition, const csrfToken, const interviewId

/* ===================================================== */
/* CONSTANTS */
/* ===================================================== */

const SILENCE_LIMIT = 5000;
let silenceTimer    = null;
let noSpeechTimer   = null;
let hasSpoken       = false;
let isListening     = false;
let mediaRecorder;
let recordedChunks  = [];
let webcamStream;

/* ===================================================== */
/* HELPERS */
/* ===================================================== */

function stopQuestionAudio() {
    const audio = document.querySelector('#question-container audio');
    if (audio) audio.pause();
}

/* ===================================================== */
/* VIDEO RECORDING */
/* ===================================================== */

async function startVideoRecording() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });

        const video = document.getElementById('candidateVideo');
        video.srcObject = webcamStream;

        // Hide overlay, show recording indicator
        const overlay = document.getElementById('videoOverlay');
        if (overlay) overlay.classList.add('hidden');

        const recIndicator = document.getElementById('recordingIndicator');
        if (recIndicator) recIndicator.classList.add('active');

        mediaRecorder = new MediaRecorder(webcamStream);

        mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
                const formData = new FormData();
                formData.append('video_chunk', event.data, `chunk_${Date.now()}.webm`);
                formData.append('interview_id', interviewId);
                await fetch('/upload_video_chunk/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                });
            }
        };

        mediaRecorder.start(30000);

    } catch (err) {
        console.error(err);
        alert('Camera/Microphone access required for the interview.');
    }
}

/* ===================================================== */
/* SHOW QUESTION */
/* ===================================================== */

function showQuestion() {
    if (currentQuestion >= questions.length) {
        finishInterview();
        return;
    }

    const q = questions[currentQuestion];
    const audioHtml = q.audio
        ? `<audio controls autoplay><source src="${q.audio}" type="audio/mpeg"></audio>`
        : '<p style="color:var(--gray-400);font-size:13px;">Audio unavailable</p>';

    document.getElementById('question-container').innerHTML = `
        <h2>Question ${currentQuestion + 1}</h2>
        <p class="q-progress">Question ${currentQuestion + 1} of ${questions.length}</p>
        <div class="q-text">${q.question}</div>
        ${audioHtml}
        <textarea
            id="answer"
            placeholder="Type your answer here, or click 'Speak Answer' to use voice input..."
        ></textarea>
        <br>
        <button type="button" onclick="startSpeechRecognition()">
            <i class="fa-solid fa-microphone"></i> Speak Answer
        </button>
        <button type="button" onclick="nextQuestion()">
            Next Question <i class="fa-solid fa-arrow-right"></i>
        </button>
    `;
}

/* ===================================================== */
/* SPEECH RECOGNITION */
/* ===================================================== */

async function startSpeechRecognition() {
    stopQuestionAudio();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Microphone access requires Chrome or Edge on HTTPS or localhost.');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(t => t.stop());
    } catch (e) {
        alert('Microphone access is blocked. Allow microphone permission for this site and try again.');
        return;
    }

    if (recognition && isListening) {
        try { recognition.stop(); } catch (e) { console.log(e); }
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Speech Recognition not supported in this browser.');
        return;
    }

    recognition             = new SpeechRecognition();
    recognition.lang        = 'en-US';
    recognition.continuous  = true;
    recognition.interimResults = true;

    let finalTranscript = '';

    recognition.onresult = function(event) {
        hasSpoken = true;
        clearTimeout(noSpeechTimer);
        clearTimeout(silenceTimer);

        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const segment = event.results[i][0].transcript;
            if (event.results[i].isFinal) finalTranscript += segment + ' ';
            else interimTranscript += segment;
        }

        document.getElementById('answer').value =
            (finalTranscript + interimTranscript).trim().replace(/\s+/g, ' ');

        silenceTimer = setTimeout(() => {
            try { recognition.stop(); } catch (e) { console.log(e); }
            nextQuestion();
        }, SILENCE_LIMIT);
    };

    recognition.onerror = function(event) {
        clearTimeout(noSpeechTimer);
        clearTimeout(silenceTimer);
        isListening = false;
        if (event.error === 'no-speech') {
            nextQuestion();
        } else if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            alert('Microphone access is blocked. Allow microphone permission for this site and try again.');
        } else if (event.error === 'audio-capture') {
            alert('No working microphone was detected. Check your microphone and browser input settings.');
        }
    };

    recognition.onend = function() { isListening = false; };

    try {
        recognition.start();
        isListening = true;
    } catch (e) {
        alert('Could not start speech recognition. Please try again.');
        return;
    }

    hasSpoken = false;
    clearTimeout(noSpeechTimer);
    noSpeechTimer = setTimeout(() => { nextQuestion(); }, SILENCE_LIMIT);
}

/* ===================================================== */
/* NEXT QUESTION */
/* ===================================================== */

function nextQuestion() {
    stopQuestionAudio();
    clearTimeout(silenceTimer);
    clearTimeout(noSpeechTimer);

    if (recognition) {
        try { recognition.stop(); } catch (e) { console.log(e); }
    }
    isListening = false;

    const answerEl = document.getElementById('answer');
    const answer   = answerEl ? answerEl.value.trim() : '';

    if (!answer) {
        const skip = confirm('No answer detected. Skip this question?');
        if (!skip) return;
    }

    questions[currentQuestion]['candidate_answer'] = answer;
    answers[currentQuestion] = {
        question: questions[currentQuestion].question,
        candidate_answer: answer
    };

    currentQuestion++;
    showQuestion();
}

/* ===================================================== */
/* FINISH INTERVIEW */
/* ===================================================== */

function finishInterview() {
    if (mediaRecorder) mediaRecorder.stop();
    if (webcamStream) webcamStream.getTracks().forEach(t => t.stop());

    const recIndicator = document.getElementById('recordingIndicator');
    if (recIndicator) recIndicator.classList.remove('active');

    document.getElementById('question-container').innerHTML = `
        <div class="completion-message">
            <i class="fa-solid fa-circle-check" style="font-size:48px;color:var(--green);margin-bottom:16px;display:block;"></i>
            <h2>Interview Completed! 🎉</h2>
            <p>All questions have been answered. Click the button below to submit your interview.</p>
            <button onclick="submitAnswers()">
                Submit Interview
            </button>
        </div>
    `;
}

/* ===================================================== */
/* SUBMIT ANSWERS */
/* ===================================================== */

function submitAnswers() {
    fetch('/submit_interview/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            interview_id: interviewId,
            questions: answers
        })
    }).then(() => {
        document.getElementById('question-container').innerHTML = `
            <div class="completion-message">
                <i class="fa-solid fa-circle-check" style="font-size:48px;color:var(--green);margin-bottom:16px;display:block;"></i>
                <h2>Interview Submitted Successfully!</h2>
                <p>Thank you for completing the interview. Your responses have been recorded.</p>
            </div>
        `;
    }).catch(error => {
        console.error('Error:', error);
        alert('Error submitting interview. Please try again.');
    });
}

/* ===================================================== */
/* INITIALIZE */
/* ===================================================== */

document.addEventListener('DOMContentLoaded', function() {
    startVideoRecording();
    showQuestion();
});
