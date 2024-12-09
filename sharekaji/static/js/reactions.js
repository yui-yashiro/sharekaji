document.querySelectorAll('.reaction-btn').forEach(button => {
    button.addEventListener('click', function () {
        const reactionList = this.nextElementSibling;

        // スタイルを直接操作して表示/非表示を切り替え
        reactionList.style.display = reactionList.style.display === 'block' ? 'none' : 'block';
    });
});

// 絵文字と数値のマッピング
const emojiMap = {
    "👍": 0,
    "💖": 1,
    "👏": 2,
    "🙇‍♀️": 3
};

document.querySelectorAll('.reaction-item').forEach(item => {
    item.addEventListener('click', function () {
        const taskId = this.getAttribute('data-task-id'); // タスクIDを取得
        const emoji = this.getAttribute('data-emoji'); // 選択された絵文字を取得
        const reactionType = emojiMap[emoji]; // 絵文字を数値に変換

        // デバッグ用
        console.log('Task ID:', taskId, 'Reaction Type:', reactionType);

        // 必須データの検証
        if (!taskId || reactionType === undefined) {
            console.error('Invalid Task ID or Reaction Type');
            return;
        }

        // サーバーへPOSTリクエストを送信
        fetch(`/tasks/${taskId}/toggle_reaction/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value, // CSRFトークンを送信
            },
            body: JSON.stringify({ reaction_type: reactionType }), // 数値データを送信
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Server response:', data);

                // リアクションの表示を更新
                const display = this.closest('.task-progress-box').querySelector('.reaction-display');
                display.innerHTML = ''; // 既存のリアクションをクリア
                data.reaction_counts.forEach(reaction => {
                    const span = document.createElement('span');
                    span.textContent = `${reaction.emoji} ${reaction.count}`;
                    display.appendChild(span);
                });
            })
            .catch(error => {
                console.error('Error during fetch:', error);
            });

        // スタンプ一覧を非表示にする
        this.parentElement.style.display = 'none';
    });
});