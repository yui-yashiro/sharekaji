document.addEventListener('DOMContentLoaded', function () {
    const formatPercentage = (value, total) => ((value / total) * 100).toFixed(1) + '%';

    // 完了タスクグラフ
    const totalCompleted = completedData.reduce((acc, value) => acc + value, 0);
    const completedCtx = document.getElementById('completedChart').getContext('2d');
    new Chart(completedCtx, {
        type: 'doughnut',
        data: {
            labels: completedLabels,
            datasets: [{
                data: completedData,
                backgroundColor: ['#336bbee7', '#2C3E50', '#fa3f06', '#98FB98', '#9370DB', '#FFA07A'],
            }]
        },
        options: {
            responsive: true,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.raw;
                            const label = context.label || '';
                            const percentage = formatPercentage(value, totalCompleted);
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                },
                datalabels: {
                    anchor: 'end',
                    align: 'end',
                    formatter: (value, context) => {
                        const percentage = formatPercentage(value, totalCompleted);
                        return `${context.chart.data.labels[context.dataIndex]}\n${percentage}`;
                    },
                    color: '#000'
                }
            }
        },
        plugins: [ChartDataLabels]
    });

    // 未完了タスクグラフ
    const totalIncomplete = incompleteData.reduce((acc, value) => acc + value, 0);
    const incompleteCtx = document.getElementById('incompletedChart').getContext('2d');
    new Chart(incompleteCtx, {
        type: 'doughnut',
        data: {
            labels: incompleteLabels,
            datasets: [{
                data: incompleteData,
                backgroundColor: ['#336bbee7', '#2C3E50', '#fa3f06', '#98FB98', '#9370DB', '#FFA07A'],
            }]
        },
        options: {
            responsive: true,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.raw;
                            const label = context.label || '';
                            const percentage = formatPercentage(value, totalIncomplete);
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                },
                datalabels: {
                    display:false,
                }
            }
        },
    });

    // グラフ切り替え機能
    const completedButton = document.querySelector('.toggle-btn-completed');
    const incompletedButton = document.querySelector('.toggle-btn-incompleted');
    const completedContainer = document.querySelector('[data-container="completed"]');
    const incompletedContainer = document.querySelector('[data-container="incompleted"]');

    if (completedButton && incompletedButton && completedContainer && incompletedContainer) {
        completedButton.addEventListener('click', () => {
            completedContainer.style.display = 'block';
            incompletedContainer.style.display = 'none';
        });

        incompletedButton.addEventListener('click', () => {
            completedContainer.style.display = 'none';
            incompletedContainer.style.display = 'block';
        });
    } else {
        console.error('直近１週間の家事はありません。');
    }
});