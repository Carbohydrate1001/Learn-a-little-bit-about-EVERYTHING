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
import hashlib
from datetime import datetime

# #region agent log
_DEBUG_LOG_PATH = r'd:\Desktop\Workspace\.cursor\debug.log'
def _dbg(location, message, data=None, hypothesis_id='', run_id=''):
    try:
        entry = json.dumps({"location": location, "message": message, "data": data or {}, "hypothesisId": hypothesis_id, "runId": run_id, "timestamp": int(time.time()*1000)}, ensure_ascii=False)
        with open(_DEBUG_LOG_PATH, 'a', encoding='utf-8') as _f: _f.write(entry + '\n')
    except: pass
# #endregion
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
        # #region agent log — Read source file BEFORE any hexo commands
        _posts_dir = get_posts_dir()
        _md_files = [f for f in os.listdir(_posts_dir) if f.endswith('.md')] if os.path.isdir(_posts_dir) else []
        _source_hashes = {}
        _source_tails = {}
        for _mf in _md_files:
            _mfp = os.path.join(_posts_dir, _mf)
            with open(_mfp, 'r', encoding='utf-8') as _rf: _mc = _rf.read()
            _source_hashes[_mf] = hashlib.md5(_mc.encode('utf-8')).hexdigest()
            _source_tails[_mf] = _mc[-80:] if len(_mc) > 80 else _mc
        _db_json_exists = os.path.exists(os.path.join(PROJECT_DIR, 'db.json'))
        _public_exists = os.path.isdir(os.path.join(PROJECT_DIR, 'public'))
        _dbg('app.py:run_deploy:START', 'Deploy starting - source state', {'source_hashes': _source_hashes, 'source_tails': _source_tails, 'db_json_exists': _db_json_exists, 'public_dir_exists': _public_exists}, hypothesis_id='A,B')
        # #endregion

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

            # #region agent log — After each command
            _post_db = os.path.exists(os.path.join(PROJECT_DIR, 'db.json'))
            _post_pub = os.path.isdir(os.path.join(PROJECT_DIR, 'public'))
            _dbg(f'app.py:run_deploy:after_{cmd.split()[1]}', f'Command "{cmd}" finished', {'returncode': process.returncode, 'db_json_exists': _post_db, 'public_dir_exists': _post_pub}, hypothesis_id='A,D')
            # #endregion

            if process.returncode != 0:
                deploy_log.append(
                    f'\n[FAIL] Command "{cmd}" failed (exit code: {process.returncode})'
                )
                with deploy_lock:
                    deploy_status = 'error'
                return

            # #region agent log — After hexo generate: check generated HTML
            if cmd == 'hexo generate':
                _pub_dir = os.path.join(PROJECT_DIR, 'public')
                _gen_hashes = {}
                if os.path.isdir(_pub_dir):
                    for _root, _dirs, _files in os.walk(_pub_dir):
                        for _gf in _files:
                            if _gf == 'index.html':
                                _gfp = os.path.join(_root, _gf)
                                _rel = os.path.relpath(_gfp, _pub_dir)
                                with open(_gfp, 'r', encoding='utf-8', errors='replace') as _ghf: _gc = _ghf.read()
                                _gen_hashes[_rel] = {'hash': hashlib.md5(_gc.encode('utf-8')).hexdigest(), 'len': len(_gc)}
                _dbg('app.py:run_deploy:after_generate_detail', 'Generated HTML files', {'generated_files': _gen_hashes}, hypothesis_id='C')
            # #endregion

            # #region agent log — After hexo deploy: check .deploy_git
            if cmd == 'hexo deploy':
                _dg_dir = os.path.join(PROJECT_DIR, '.deploy_git')
                _dg_hashes = {}
                if os.path.isdir(_dg_dir):
                    for _root, _dirs, _files in os.walk(_dg_dir):
                        if '.git' in _root: continue
                        for _dgf in _files:
                            if _dgf == 'index.html':
                                _dgfp = os.path.join(_root, _dgf)
                                _rel = os.path.relpath(_dgfp, _dg_dir)
                                with open(_dgfp, 'r', encoding='utf-8', errors='replace') as _dghf: _dgc = _dghf.read()
                                _dg_hashes[_rel] = {'hash': hashlib.md5(_dgc.encode('utf-8')).hexdigest(), 'len': len(_dgc)}
                _dbg('app.py:run_deploy:after_deploy_detail', 'Deploy_git HTML files', {'deploy_git_files': _dg_hashes}, hypothesis_id='C')
            # #endregion

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
        # #region agent log
        _saved_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        with open(filepath, 'r', encoding='utf-8') as _vf: _verify_content = _vf.read()
        _verify_hash = hashlib.md5(_verify_content.encode('utf-8')).hexdigest()
        _dbg('app.py:edit_post:POST', 'File saved and verified', {'filename': filename, 'content_len': len(content), 'saved_hash': _saved_hash, 'readback_hash': _verify_hash, 'last_80_chars': content[-80:] if len(content) > 80 else content, 'match': _saved_hash == _verify_hash}, hypothesis_id='B')
        # #endregion
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
