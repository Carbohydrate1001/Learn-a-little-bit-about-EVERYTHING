"""
CarboBlogManager - Hexo 博客管理 Web 系统
==========================================
基于 Flask 的本地 Web 应用，提供文章增删改查、Markdown 编辑预览、
图片上传以及一键部署到 GitHub Pages 的功能。
"""

import os
import sys
import json
import subprocess
import threading
import webbrowser
import argparse
import time
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, Response, send_from_directory
)

# ============================================================
# Path Resolution (compatible with PyInstaller)
# ============================================================

def get_base_dir():
    """Get the base directory for templates and static files.
    When frozen by PyInstaller, resources are extracted to sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def find_hexo_project():
    """Auto-detect Hexo project directory by searching for _config.yml."""
    # 1. Command-line argument
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--project-dir', type=str, default=None)
    args, _ = parser.parse_known_args()
    if args.project_dir:
        p = os.path.abspath(args.project_dir)
        if os.path.isfile(os.path.join(p, '_config.yml')):
            return p

    # 2. Search upward from multiple starting points
    search_starts = [
        os.path.dirname(os.path.abspath(__file__)),   # script dir
        os.getcwd(),                                    # working dir
    ]
    if getattr(sys, 'frozen', False):
        search_starts.append(os.path.dirname(sys.executable))

    for start in search_starts:
        current = os.path.abspath(start)
        for _ in range(5):                              # up to 5 levels
            if os.path.isfile(os.path.join(current, '_config.yml')):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    return None


# ============================================================
# Flask App Setup
# ============================================================

BASE_DIR = get_base_dir()
PROJECT_DIR = find_hexo_project()

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)
app.secret_key = 'carbospace-blog-manager-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit


# ============================================================
# Helper Functions
# ============================================================

def get_posts_dir():
    return os.path.join(PROJECT_DIR, 'source', '_posts')


def get_images_dir():
    img_dir = os.path.join(PROJECT_DIR, 'source', 'images')
    os.makedirs(img_dir, exist_ok=True)
    return img_dir


def parse_front_matter(content):
    """Parse YAML front-matter from markdown content.
    Returns (dict, body_string).
    """
    if not content.startswith('---'):
        return {}, content

    end = content.find('---', 3)
    if end == -1:
        return {}, content

    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()

    fm = {}
    current_key = None
    current_list = None

    for line in fm_text.split('\n'):
        stripped = line.rstrip()
        if not stripped:
            continue

        # List item (  - value)
        if stripped.startswith('  - ') or stripped.startswith('\t- '):
            value = stripped.lstrip(' \t-').strip()
            if current_key is not None and isinstance(current_list, list):
                current_list.append(value)
            continue

        # Key: value pair
        if ':' in stripped:
            # Save previous list
            if current_key and current_list is not None:
                fm[current_key] = current_list

            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()

            if value:
                fm[key] = value
                current_key = None
                current_list = None
            else:
                current_key = key
                current_list = []

    # Save last pending list
    if current_key and current_list is not None:
        fm[current_key] = current_list

    return fm, body


def list_posts():
    """Return a list of post metadata dicts, sorted by date descending."""
    posts_dir = get_posts_dir()
    posts = []

    if not os.path.isdir(posts_dir):
        return posts

    for filename in os.listdir(posts_dir):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(posts_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        fm, body = parse_front_matter(content)

        posts.append({
            'filename': filename,
            'title': fm.get('title', filename.replace('.md', '')),
            'date': fm.get('date', ''),
            'tags': fm.get('tags', []) if isinstance(fm.get('tags'), list) else [],
            'categories': fm.get('categories', []) if isinstance(fm.get('categories'), list) else [],
            'excerpt': body[:200] + '...' if len(body) > 200 else body,
        })

    posts.sort(key=lambda p: str(p.get('date', '')), reverse=True)
    return posts


def generate_front_matter(title, tags=None, categories=None):
    """Generate YAML front-matter string for a new post."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = ['---']
    lines.append(f'title: {title}')
    lines.append(f'date: {now}')

    if tags:
        lines.append('tags:')
        for tag in tags:
            tag = tag.strip()
            if tag:
                lines.append(f'  - {tag}')
    else:
        lines.append('tags:')

    if categories:
        lines.append('categories:')
        for cat in categories:
            cat = cat.strip()
            if cat:
                lines.append(f'  - {cat}')

    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


# ============================================================
# Deploy State (shared across threads)
# ============================================================

deploy_log: list[str] = []
deploy_status: str = 'idle'  # idle | running | success | error
deploy_lock = threading.Lock()


def run_deploy():
    """Execute hexo clean → generate → deploy in a background thread."""
    global deploy_log, deploy_status

    with deploy_lock:
        if deploy_status == 'running':
            return
        deploy_log = []
        deploy_status = 'running'

    commands = [
        ('hexo clean',    '[1/3] Cleaning generated files...'),
        ('hexo generate', '[2/3] Generating static files...'),
        ('hexo deploy',   '[3/3] Deploying to GitHub Pages...'),
    ]

    try:
        for cmd, label in commands:
            deploy_log.append(f'\n{label}')
            deploy_log.append(f'$ {cmd}')

            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
            )

            for line in iter(process.stdout.readline, ''):
                deploy_log.append(line.rstrip())

            process.wait()

            if process.returncode != 0:
                deploy_log.append(
                    f'\n[FAIL] Command "{cmd}" failed (exit code: {process.returncode})'
                )
                with deploy_lock:
                    deploy_status = 'error'
                return

            deploy_log.append(f'[OK] {cmd} completed.')

        deploy_log.append('\n[SUCCESS] Deploy completed!')
        deploy_log.append('Visit: https://carbohydrate1001.github.io')
        with deploy_lock:
            deploy_status = 'success'

    except Exception as e:
        deploy_log.append(f'\n[ERROR] {str(e)}')
        with deploy_lock:
            deploy_status = 'error'


# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    if not PROJECT_DIR:
        return render_template(
            'index.html', posts=[],
            error='未找到 Hexo 项目目录。请使用 --project-dir 参数指定路径。'
        )
    posts = list_posts()
    return render_template('index.html', posts=posts, project_dir=PROJECT_DIR)


@app.route('/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        tags_raw = request.form.get('tags', '')
        cats_raw = request.form.get('categories', '')
        body = request.form.get('content', '')

        tags = [t for t in tags_raw.split(',') if t.strip()] if tags_raw else []
        categories = [c for c in cats_raw.split(',') if c.strip()] if cats_raw else []

        if not title:
            flash('标题不能为空', 'error')
            return redirect(url_for('new_post'))

        # Build filename
        filename = title.replace(' ', '-') + '.md'
        filepath = os.path.join(get_posts_dir(), filename)

        if os.path.exists(filepath):
            flash(f'文件 {filename} 已存在，请使用其他标题', 'error')
            return redirect(url_for('new_post'))

        os.makedirs(get_posts_dir(), exist_ok=True)

        fm = generate_front_matter(title, tags, categories)
        # Normalize line endings from browser form
        body = body.replace('\r\n', '\n').replace('\r', '\n')
        full_content = fm + body

        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(full_content)

        flash(f'文章 「{title}」 创建成功！', 'success')
        return redirect(url_for('edit_post', filename=filename))

    return render_template(
        'editor.html', mode='new',
        filename='', content='', title='', tags='', categories=''
    )


@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_post(filename):
    filepath = os.path.join(get_posts_dir(), filename)

    if not os.path.exists(filepath):
        flash(f'文件 {filename} 不存在', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        content = request.form.get('content', '')
        # Normalize line endings: browser sends \r\n which becomes \r\r\n in Windows text mode
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        flash('保存成功！', 'success')
        return redirect(url_for('edit_post', filename=filename))

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, _ = parse_front_matter(content)

    return render_template(
        'editor.html', mode='edit',
        filename=filename, content=content,
        title=fm.get('title', ''),
        tags=(', '.join(fm['tags']) if isinstance(fm.get('tags'), list) else ''),
        categories=(', '.join(fm['categories']) if isinstance(fm.get('categories'), list) else ''),
    )


@app.route('/delete/<filename>', methods=['POST'])
def delete_post(filename):
    filepath = os.path.join(get_posts_dir(), filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f'文章 「{filename}」 已删除', 'success')
    else:
        flash(f'文件 {filename} 不存在', 'error')
    return redirect(url_for('index'))


@app.route('/preview/<filename>')
def preview_post(filename):
    filepath = os.path.join(get_posts_dir(), filename)

    if not os.path.exists(filepath):
        flash(f'文件 {filename} 不存在', 'error')
        return redirect(url_for('index'))

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, body = parse_front_matter(content)

    return render_template(
        'preview.html',
        filename=filename,
        title=fm.get('title', filename),
        date=fm.get('date', ''),
        tags=fm.get('tags', []) if isinstance(fm.get('tags'), list) else [],
        content=body,
    )


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    original_name = file.filename.replace(' ', '_')
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in allowed_ext:
        return jsonify({'error': f'不支持的文件格式: {ext}'}), 400

    filename = original_name
    save_path = os.path.join(get_images_dir(), filename)

    # Avoid overwrite: append timestamp
    if os.path.exists(save_path):
        name_part = os.path.splitext(filename)[0]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f'{name_part}_{timestamp}{ext}'
        save_path = os.path.join(get_images_dir(), filename)

    file.save(save_path)

    md_path = f'/images/{filename}'
    return jsonify({
        'success': True,
        'filename': filename,
        'path': md_path,
        'markdown': f'![{filename}]({md_path})',
    })


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve uploaded images so the editor preview can display them."""
    return send_from_directory(get_images_dir(), filename)


@app.route('/api/images')
def api_list_images():
    """Return a JSON list of all uploaded images."""
    images_dir = get_images_dir()
    images = []
    allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}

    if os.path.isdir(images_dir):
        for f in sorted(os.listdir(images_dir)):
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_ext:
                images.append({
                    'filename': f,
                    'path': f'/images/{f}',
                    'markdown': f'![{f}](/images/{f})',
                })

    return jsonify(images)


# ----- Deploy Endpoints -----

@app.route('/deploy', methods=['POST'])
def deploy():
    if deploy_status == 'running':
        return jsonify({'error': '部署正在进行中...'}), 409

    thread = threading.Thread(target=run_deploy, daemon=True)
    thread.start()
    return jsonify({'message': '部署已开始'}), 202


@app.route('/deploy/stream')
def deploy_stream():
    """SSE endpoint that streams deploy log lines in real-time."""
    def generate():
        last_index = 0
        while True:
            current_len = len(deploy_log)
            current_status = deploy_status

            if last_index < current_len:
                for i in range(last_index, current_len):
                    msg = deploy_log[i]
                    data = json.dumps(
                        {'type': 'log', 'message': msg}, ensure_ascii=False
                    )
                    yield f'data: {data}\n\n'
                last_index = current_len

            if current_status in ('success', 'error'):
                data = json.dumps(
                    {'type': 'done', 'status': current_status},
                    ensure_ascii=False,
                )
                yield f'data: {data}\n\n'
                break

            time.sleep(0.3)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


@app.route('/deploy/status')
def deploy_status_api():
    return jsonify({'status': deploy_status, 'log_count': len(deploy_log)})


# ============================================================
# Main Entry
# ============================================================

def open_browser():
    """Open the management page in the default browser after a short delay."""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    if not PROJECT_DIR:
        print('=' * 60)
        print('  ERROR: Hexo project directory not found!')
        print()
        print('  Please specify the project path using one of:')
        print('    1. Place this program under carbospace/blog_manager/')
        print('    2. Run from the Hexo project root (with _config.yml)')
        print('    3. Use argument: python app.py --project-dir <path>')
        print('=' * 60)
        sys.exit(1)

    print('=' * 60)
    print('  CarboBlogManager')
    print('  Hexo Project: ' + PROJECT_DIR)
    print('  Posts Dir:    ' + get_posts_dir())
    print('  Images Dir:   ' + get_images_dir())
    print('  Web UI:       http://localhost:5000')
    print('=' * 60)

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
