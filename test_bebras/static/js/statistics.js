document.addEventListener('DOMContentLoaded', function() {
    Chart.register(ChartDataLabels);

    const userAttemptsDataElement = document.querySelector('script[type="application/json"][data-id="user_attempt_counts_json"]');
    const overallPerformanceDataElement = document.querySelector('script[type="application/json"][data-id="overall_performance_json"]');
    const skillPerformanceDataElement = document.querySelector('script[type="application/json"][data-id="skill_performance_data_json"]');

    let userAttemptsData = [];
    let overallPerformanceData = {};
    let skillPerformanceData = [];

    if (userAttemptsDataElement) {
        userAttemptsData = JSON.parse(userAttemptsDataElement.textContent);
    }
    if (overallPerformanceDataElement) {
        overallPerformanceData = JSON.parse(overallPerformanceDataElement.textContent);
    }
    if (skillPerformanceDataElement) {
        skillPerformanceData = JSON.parse(skillPerformanceDataElement.textContent);
    }

    if (overallPerformanceData && overallPerformanceData.total_attempts_count > 0) {
        const overallLabels = ['Correctas', 'Incorrectas', 'No Respondidas'];
        const overallCounts = [
            overallPerformanceData.correct,
            overallPerformanceData.incorrect,
            overallPerformanceData.unanswered
        ];
        const overallColors = ['#28a745', '#dc3545', '#ffc107'];

        const overallPerformanceCtx = document.getElementById('overallPerformanceChart').getContext('2d');
        new Chart(overallPerformanceCtx, {
            type: 'pie',
            data: {
                labels: overallLabels,
                datasets: [{
                    data: overallCounts,
                    backgroundColor: overallColors,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false,
                        text: 'Rendimiento General'
                    },
                    datalabels: {
                        formatter: (value, context) => {
                            const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? (value / total * 100).toFixed(1) + '%' : '0%';
                            return value + ' (' + percentage + ')';
                        },
                        color: '#fff',
                        font: {
                            weight: 'bold'
                        }
                    }
                }
            }
        });
    } else {
        const overallPerformanceCtx = document.getElementById('overallPerformanceChart');
        if (overallPerformanceCtx) {
            overallPerformanceCtx.style.display = 'none';
            const messageElement = overallPerformanceCtx.parentNode.querySelector('.text-muted.text-center.mt-3');
            if (messageElement) messageElement.style.display = 'block';
        }
    }

    if (skillPerformanceData && skillPerformanceData.length > 0) {
        const skillLabels = skillPerformanceData.map(item => item.skill_name);
        const correctData = skillPerformanceData.map(item => item.correct);
        const incorrectData = skillPerformanceData.map(item => item.incorrect);

        const skillPerformanceCtx = document.getElementById('skillPerformanceChart').getContext('2d');
        new Chart(skillPerformanceCtx, {
            type: 'bar',
            data: {
                labels: skillLabels,
                datasets: [
                    {
                        label: 'Correctas',
                        data: correctData,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Incorrectas',
                        data: incorrectData,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 20
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: false,
                        text: 'Rendimiento por Habilidad'
                    },
                    datalabels: {
                        anchor: 'center', 
                        align: 'center',
                        offset: 5, 
                        formatter: (value, context) => value.toFixed(0),
                        font: {
                            weight: 'bold'
                        },
                        color: '#000' 
                    }    
                },
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Habilidad'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        },
                        title: {
                            display: true,
                            text: 'Cantidad'
                        },
                        suggestedMax: 10
                    }
                }
            }
        });
    } else {
        const skillPerformanceCtx = document.getElementById('skillPerformanceChart');
        if (skillPerformanceCtx) {
            skillPerformanceCtx.style.display = 'none';
            const messageElement = skillPerformanceCtx.parentNode.querySelector('.text-muted.text-center.mt-3');
            if (messageElement) messageElement.style.display = 'block';
        }
    }
});