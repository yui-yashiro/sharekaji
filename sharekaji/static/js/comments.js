(function () {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // コメント削除処理
    const addDeleteListener = (deleteButton) => {
        deleteButton.addEventListener('click', () => {
            const commentId = deleteButton.getAttribute('data-comment-id');
            if (!commentId) {
                console.error('コメントIDが見つかりません');
                return;
            }

            fetch(`/comments/delete/${commentId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    // コメントを削除
                    document.querySelector(`#comment-${commentId}`).remove();
                })
                .catch(error => {
                    console.error('コメント削除中にエラーが発生しました:', error);
                    alert('コメント削除に失敗しました。再試行してください。');
                });
        });
    };

    // コメント送信処理
    document.querySelectorAll('.send-comment-btn').forEach(button => {
        button.addEventListener('click', () => {
            const taskId = button.getAttribute('data-task-id');
            const commentInput = button.previousElementSibling;
            const commentText = commentInput.value.trim();

            if (!commentText) {
                alert('コメントを入力してください。');
                return;
            }

            fetch('/comments/add/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ comment: commentText, task_id: taskId }),
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }

                    // 新しいコメントを追加
                    const commentList = document.querySelector(`#comments-list-${taskId}`);
                    const newComment = `
                        <div class="comment-box border p-3 mb-2 rounded d-flex align-items-center" id="comment-${data.id}">
                            <img src="${data.avatar || '/media/default_profile_image.png'}"
                                alt="avatar" 
                                class="rounded-circle mr-2" 
                                style="width: 40px; height: 40px;">
                            <div>
                                <strong>${data.user}</strong>
                                <p class="mb-1">${data.comment}</p>
                            </div>
                            <button class="delete-comment-btn btn btn-sm btn-danger ml-auto" data-comment-id="${data.id}">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    `;
                    commentList.insertAdjacentHTML('beforeend', newComment);
                    commentInput.value = '';

                    // 削除ボタンのイベントリスナーを追加
                    const deleteButton = commentList.querySelector(`#comment-${data.id} .delete-comment-btn`);
                    addDeleteListener(deleteButton);
                })
                .catch(error => {
                    console.error('コメント送信中にエラーが発生しました:', error);
                });
        });
    });

    // 既存の削除ボタンにもリスナーを追加
    document.querySelectorAll('.delete-comment-btn').forEach(addDeleteListener);
})();