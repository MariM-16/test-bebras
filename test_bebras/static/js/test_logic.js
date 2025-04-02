document.addEventListener("DOMContentLoaded", function() {
    let form = document.getElementById("test-form");
    let button = document.querySelector(".btn-next");
    let inputs = form.querySelectorAll("input");
    let timerElement = document.getElementById("timer");
    let timerContainer = document.querySelector(".timer");

    let totalTestTime = parseInt(timerContainer.dataset.timeLimit, 10);
    let savedTimeLeft = localStorage.getItem("timeLeft");
    
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

    let allowBacktracking = timerContainer.dataset.allowBacktracking === "true";

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
            localStorage.removeItem("timeLeft"); 
            form.submit();
        } else {
            localStorage.setItem("timeLeft", timeLeft); 
            timeLeft--;
        }
    }

    let timerInterval = setInterval(updateTimer, 1000);
});
