document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("test-form");
    const button = document.querySelector(".btn-next");
    const inputs = form.querySelectorAll("input");
    const timerElement = document.getElementById("timer");
    const timerContainer = document.querySelector(".timer");

    const totalTestTime = parseInt(timerContainer.dataset.timeLimit, 10);
    const testId = timerContainer.dataset.testId;
    const attemptId = timerContainer.dataset.attemptId;
    const allowBacktracking = timerContainer.dataset.allowBacktracking === "true";

    const storageKey = `timeLeft-${testId}-${attemptId}`;

    const savedTimeLeft = localStorage.getItem(storageKey);
    let timeLeft = savedTimeLeft ? parseInt(savedTimeLeft, 10) : totalTestTime;

    function checkInput() {
        let isFilled = false;
        inputs.forEach(input => {
            if ((input.type === "radio" && input.checked) ||
                (input.type !== "radio" && input.value.trim() !== "")) {
                isFilled = true;
            }
        });
        button.disabled = !isFilled;
    }

    inputs.forEach(input => {
        input.addEventListener("input", checkInput);
        input.addEventListener("change", checkInput);
    });

    if (!allowBacktracking) {
        window.history.pushState(null, "", window.location.href);
        window.onpopstate = function () {
            window.history.pushState(null, "", window.location.href);
        };
    }

    function updateTimer() {
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;
        timerElement.innerText = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            localStorage.removeItem(storageKey);
            form.submit();
            handleTimeout();
        } else {
            localStorage.setItem(storageKey, timeLeft);
            timeLeft--;
        }
    }

    // Limpiar tiempo si el usuario envía el formulario (termina el test)
    form.addEventListener("submit", function () {
        localStorage.removeItem(storageKey);
    });

    let timerInterval = setInterval(updateTimer, 1000);

    Object.keys(localStorage).forEach(function(key) {
        if (key.startsWith("timeLeft-")) {
            localStorage.removeItem(key);
        }
    });

    function handleTimeout() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = window.location.href;
    
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
    
        const forceInput = document.createElement('input');
        forceInput.type = 'hidden';
        forceInput.name = 'force_finish';
        forceInput.value = 'true';
        form.appendChild(forceInput);
    
        document.body.appendChild(form);
        form.submit();
    }
    
});
