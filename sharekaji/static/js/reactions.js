(function () {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // リアクションボタンのクリックイベント
    document.querySelectorAll('.reaction-btn').forEach(button => {
        button.addEventListener('click', function () {
            const reactionList = this.nextElementSibling;
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

    // スタンプ一覧の各ボタンにクリックイベントを設定
    document.querySelectorAll('.reaction-item').forEach(item => {
        item.addEventListener('click', function () {
            const taskId = this.getAttribute('data-task-id'); // タスクIDを取得
            const emoji = this.getAttribute('data-emoji');    // 選択された絵文字を取得
            const reactionType = emojiMap[emoji];             // 絵文字を数値に変換

            // デバッグ用の出力
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
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ reaction_type: reactionType }),
            })
                .then(response => {
                    console.log('HTTP Status:', response.status); // HTTPステータス確認
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Server response:', data);

                    // サーバーからエラーが返ってきた場合
                    if (data.error) {
                        console.error('Server Error:', data.error);
                        return;
                    }

                    // リアクションの表示を更新
                    const display = this.closest('.task-progress-box').querySelector('.reaction-display');
                    display.innerHTML = ''; // 既存のリアクションをクリア

                    // 新しいリアクションを表示
                    data.reaction_counts.forEach(reaction => {
                        const span = document.createElement('span');
                        span.textContent = `${reaction.emoji} ${reaction.count}`;
                        display.appendChild(span);
                    });
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                });

            // スタンプ一覧を非表示にする
            this.parentElement.style.display = 'none';
        });
    });
})();