document.addEventListener('DOMContentLoaded', function () {
    // 完了タスクグラフ
    const completedCtx = document.getElementById('completedChart').getContext('2d');
    new Chart(completedCtx, {
        type: 'doughnut',
        data: {
            labels: completedLabels,
            datasets: [{
                data: completedData,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });

    // 未完了タスクグラフ
    const incompleteCtx = document.getElementById('incompletedChart').getContext('2d');
    new Chart(incompleteCtx, {
        type: 'doughnut',
        data: {
            labels: incompleteLabels,
            datasets: [{
                data: incompleteData,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });

    // グラフ切り替え機能
    const buttons = document.querySelectorAll('.toggle-btn');
    const completedContainer = document.querySelector('[data-container="completed"]');
    const incompleteContainer = document.querySelector('[data-container="incompleted"]');

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const target = button.getAttribute('data-target');
            if (target === 'completed') {
                completedContainer.style.display = 'block';
                incompleteContainer.style.display = 'none';
            } else {
                completedContainer.style.display = 'none';
                incompleteContainer.style.display = 'block';
            }
        });
    });
});