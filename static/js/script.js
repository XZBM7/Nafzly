$(document).ready(function () {
    
    $('.like-btn').click(function () {
        const postId = $(this).data('post-id');
        const likeBtn = $(this);

        $.ajax({
            url: `/like_post/${postId}`,
            method: 'POST',
            success: function (response) {
                if (response.success) {
                    likeBtn.find('.like-count').text(response.likes_count);
                    likeBtn.prop('disabled', true).removeClass('btn-outline-primary').addClass('btn-primary');
                }
            },
            error: function (xhr) {
                alert(xhr.responseJSON.message || 'حدث خطأ أثناء الإعجاب بالمنشور');
            }
        });
    });

    
    $('.save-btn').click(function () {
        const postId = $(this).data('post-id');
        const saveBtn = $(this);

        $.ajax({
            url: `/save_post/${postId}`,
            method: 'POST',
            success: function (response) {
                if (response.success) {
                    saveBtn.prop('disabled', true).removeClass('btn-outline-success').addClass('btn-success');
                    saveBtn.html('<i class="fas fa-bookmark"></i> محفوظ');
                }
            },
            error: function (xhr) {
                alert(xhr.responseJSON.message || 'حدث خطأ أثناء حفظ المنشور');
            }
        });
    });

    
    $('.comment-btn').click(function () {
        const postId = $(this).data('post-id');
        const section = $(`#comments-${postId}`);

        if (section.is(':visible')) {
            section.hide();
        } else {
            if (section.find('.comments-list').children().length === 0) {
                loadComments(postId);
            }
            section.show();
        }
    });

    
    $('.comment-form').submit(function (e) {
        e.preventDefault();

        const postId = $(this).data('post-id');
        const input = $(this).find('.comment-input');
        const content = input.val().trim();

        if (content) {
            $.ajax({
                url: `/comment_post/${postId}`,
                method: 'POST',
                data: { content: content },
                success: function (response) {
                    if (response.success) {
                        const list = $(`#comments-${postId} .comments-list`);
                        const newComment = `
                            <div class="card mb-2">
                                <div class="card-body p-2">
                                    <strong>${response.comment.username}</strong>
                                    <p class="mb-0">${response.comment.content}</p>
                                    <small class="text-muted">${response.comment.created_at}</small>
                                </div>
                            </div>
                        `;
                        list.prepend(newComment);
                        input.val('');
                        $(`.comment-btn[data-post-id="${postId}"] .comment-count`).text(response.comments_count);
                    }
                },
                error: function (xhr) {
                    alert(xhr.responseJSON.message || 'حدث خطأ أثناء إضافة التعليق');
                }
            });
        }
    });

    
    function loadComments(postId) {
        $.ajax({
            url: `/get_comments/${postId}`,
            method: 'GET',
            success: function (response) {
                if (response.success) {
                    const list = $(`#comments-${postId} .comments-list`);
                    list.empty();

                    response.comments.forEach(comment => {
                        const html = `
                            <div class="card mb-2">
                                <div class="card-body p-2">
                                    <strong>${comment.username}</strong>
                                    <p class="mb-0">${comment.content}</p>
                                    <small class="text-muted">${comment.created_at}</small>
                                </div>
                            </div>
                        `;
                        list.append(html);
                    });
                }
            },
            error: function () {
                alert('حدث خطأ أثناء تحميل التعليقات');
            }
        });
    }
});
