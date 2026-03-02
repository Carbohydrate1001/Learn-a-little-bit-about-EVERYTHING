/**
 * CarboBlogManager - Frontend Interaction Logic
 * ==============================================
 * Handles: search filtering, delete confirmation, deploy panel,
 *          image upload (drag & drop), and flash message auto-dismiss.
 */

// ============================================================
// Search / Filter Posts
// ============================================================

function filterPosts() {
    const query = document.getElementById('search-input').value.toLowerCase().trim();
    const cards = document.querySelectorAll('.post-card');

    cards.forEach(function(card) {
        const title = (card.dataset.title || '').toLowerCase();
        const tags  = (card.dataset.tags  || '').toLowerCase();
        const match = title.includes(query) || tags.includes(query);
        card.style.display = match ? '' : 'none';
    });
}


// ============================================================
// Delete Confirmation Modal
// ============================================================

function confirmDelete(filename, title) {
    document.getElementById('delete-title').textContent = title;
    document.getElementById('delete-form').action = '/delete/' + encodeURIComponent(filename);
    document.getElementById('delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
}

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});


// ============================================================
// Deploy Panel
// ============================================================

let deployEventSource = null;

function startDeploy() {
    if (!confirm('确定要部署到 GitHub Pages 吗？\n\n将执行: hexo clean → generate → deploy')) {
        return;
    }

    const panel  = document.getElementById('deploy-panel');
    const log    = document.getElementById('deploy-log');
    const status = document.getElementById('deploy-status');
    const btn    = document.getElementById('deploy-btn');

    // Reset & show panel
    panel.classList.remove('hidden');
    log.innerHTML = '';
    status.textContent = '';
    status.className = 'deploy-status';
    btn.disabled = true;
    btn.innerHTML = '<span class="nav-icon">⏳</span> 部署中...';

    // Trigger deploy
    fetch('/deploy', { method: 'POST' })
        .then(function(resp) {
            if (resp.status === 409) {
                alert('部署正在进行中，请等待完成。');
                btn.disabled = false;
                btn.innerHTML = '<span class="nav-icon">▲</span> 部署上线';
                return;
            }

            // Close previous SSE if any
            if (deployEventSource) {
                deployEventSource.close();
            }

            // Open SSE stream
            deployEventSource = new EventSource('/deploy/stream');

            deployEventSource.onmessage = function(event) {
                var data = JSON.parse(event.data);

                if (data.type === 'log') {
                    var line = document.createElement('div');
                    line.className = 'log-line';
                    line.textContent = data.message;
                    log.appendChild(line);
                    log.scrollTop = log.scrollHeight;
                }

                if (data.type === 'done') {
                    deployEventSource.close();
                    deployEventSource = null;
                    btn.disabled = false;
                    btn.innerHTML = '<span class="nav-icon">▲</span> 部署上线';

                    if (data.status === 'success') {
                        status.textContent = '✅ 部署成功！';
                        status.className = 'deploy-status success';
                    } else {
                        status.textContent = '❌ 部署失败';
                        status.className = 'deploy-status error';
                    }
                }
            };

            deployEventSource.onerror = function() {
                deployEventSource.close();
                deployEventSource = null;
                btn.disabled = false;
                btn.innerHTML = '<span class="nav-icon">▲</span> 部署上线';
                status.textContent = '⚠ 连接中断';
                status.className = 'deploy-status error';
            };
        })
        .catch(function(err) {
            btn.disabled = false;
            btn.innerHTML = '<span class="nav-icon">▲</span> 部署上线';
            alert('部署请求失败: ' + err.message);
        });
}

function toggleDeployPanel() {
    document.getElementById('deploy-panel').classList.toggle('hidden');
}


// ============================================================
// Image Upload
// ============================================================

function uploadFile(file) {
    if (!file) return;

    var resultDiv = document.getElementById('upload-result');
    if (!resultDiv) return;

    resultDiv.classList.remove('hidden');
    resultDiv.className = 'upload-result';
    resultDiv.textContent = '⏳ 上传中...';

    var formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData,
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
        if (data.error) {
            resultDiv.textContent = '❌ ' + data.error;
            resultDiv.className = 'upload-result error';
        } else {
            resultDiv.innerHTML =
                '✅ 上传成功！Markdown 引用：' +
                '<code class="copy-code" onclick="copyToClipboard(this)" title="点击复制">' +
                escapeHtml(data.markdown) +
                '</code>' +
                ' <small style="color:var(--text-muted);">点击复制</small>';
            resultDiv.className = 'upload-result success';
        }
    })
    .catch(function(err) {
        resultDiv.textContent = '❌ 上传失败: ' + err.message;
        resultDiv.className = 'upload-result error';
    });
}


// ============================================================
// Drag & Drop for Upload Area
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    var uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');

            if (e.dataTransfer.files.length > 0) {
                uploadFile(e.dataTransfer.files[0]);
            }
        });
    }

    // Auto-dismiss flash messages after 4 seconds
    setTimeout(function() {
        document.querySelectorAll('.flash').forEach(function(el) {
            el.style.transition = 'opacity 0.4s';
            el.style.opacity = '0';
            setTimeout(function() { el.remove(); }, 400);
        });
    }, 4000);
});


// ============================================================
// Utilities
// ============================================================

function copyToClipboard(element) {
    var text = element.textContent;
    navigator.clipboard.writeText(text).then(function() {
        var original = element.textContent;
        element.textContent = '✅ 已复制！';
        element.style.color = 'var(--accent-green)';
        setTimeout(function() {
            element.textContent = original;
            element.style.color = '';
        }, 1500);
    }).catch(function() {
        // Fallback: select text
        var range = document.createRange();
        range.selectNodeContents(element);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    });
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
