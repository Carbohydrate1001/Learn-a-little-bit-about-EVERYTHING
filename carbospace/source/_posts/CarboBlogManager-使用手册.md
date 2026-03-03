---
title: CarboBlogManager 使用手册
date: 2026-03-03 10:49:05
tags:
  - Vibe coding
  - Tools
---
# CarboBlogManager：一个轻量的 Hexo 博客本地管理器

CarboBlogManager 是为 Carbospace 博客编写的本地管理工具。它基于 Flask 构建，提供一个 Web 界面，用来完成文章的增删改查、Markdown 编辑与预览、图片上传，以及向 GitHub Pages 的一键部署。

本文记录它的使用方法与注意事项。

---

## 环境要求

管理器的运行依赖以下工具：

| 工具 | 最低版本 | 用途 | 检查命令 |
| --- | --- | --- | --- |
| Python | 3.8+ | 运行管理器（脚本模式） | `python --version` |
| Node.js | 14.x | 运行 Hexo 命令 | `node -v` |
| npm | 6.x | 管理 Hexo 依赖 | `npm -v` |
| Git | 2.x | 部署推送到 GitHub | `git --version` |
| Hexo CLI | 4.x | 执行 hexo 命令 | `hexo version` |

此外，本机的 SSH 公钥需要已添加到 GitHub 账户，部署通过 SSH 推送完成。`carbospace/` 目录下也需要已经执行过 `npm install`，确保 `node_modules/` 存在。

如果使用打包后的 `.exe` 运行，可以不安装 Python，但 Node.js、Git 和 Hexo CLI 仍然是必须的。

---

## 启动

### 脚本模式

进入 `carbospace/blog_manager` 目录，安装依赖后启动：

```bash
cd carbospace/blog_manager
pip install flask
python app.py
```

管理器会自动向上级目录搜索 `_config.yml` 来定位 Hexo 项目，然后在 `http://localhost:5000` 启动服务，并打开浏览器。

如果自动检测失败，可以手动指定路径：

```bash
python app.py --project-dir "D:\path\to\carbospace"
```

### 可执行程序模式

先完成打包：

```bash
cd carbospace/blog_manager
pip install -r requirements.txt
build.bat
```

打包完成后，`dist/` 目录下会生成 `CarboBlogManager.exe`。将它放到 `carbospace/` 目录下双击运行即可。也可以在其他位置通过参数指定项目路径：

```bash
CarboBlogManager.exe --project-dir "D:\path\to\carbospace"
```

---

## 功能

### 仪表盘

访问 `http://localhost:5000/` 进入仪表盘。页面以卡片形式展示 `source/_posts/` 中的所有 `.md` 文章，每张卡片包含标题、日期、标签和正文摘要。

页面顶部有一个搜索框，输入关键词可以实时过滤文章。每张卡片上提供编辑、预览和删除三个操作入口。

### 新建文章

点击导航栏的「新建文章」或访问 `/new`，填写标题（必填）、标签和分类（选填，逗号分隔），以及正文内容。

提交后，系统自动生成包含 `title`、`date`、`tags`、`categories` 的 YAML Front-matter，在 `source/_posts/` 下创建 `.md` 文件，并跳转到编辑器继续编写。生成的 Front-matter 形如：

```yaml
---
title: 深度学习入门笔记
date: 2026-03-02 17:30:00
tags:
  - Deep Learning
  - Python
categories:
  - 技术笔记
---
```

### 编辑文章

编辑器基于 EasyMDE，工具栏涵盖常用的 Markdown 格式操作：粗体、标题、列表、链接、代码块、表格等。支持实时预览、分屏模式和全屏写作。编辑器每 5 秒自动将内容保存到浏览器本地存储，防止意外丢失。

需要注意的是，编辑器中显示的是完整文件内容，包括 Front-matter。直接修改 Front-matter 中的字段即可生效。点击「保存」将内容写入磁盘。

### 删除文章

在仪表盘点击文章卡片上的「删除」按钮，确认后文件从 `source/_posts/` 中移除。此操作不可撤销，如需恢复请借助 Git 版本历史。

### Markdown 预览

访问 `/preview/<filename>` 可以查看文章的渲染效果。页面使用 marked.js 渲染 Markdown，highlight.js 高亮代码块，展示标题、日期、标签和完整正文。

### 图片上传

编辑文章时，编辑器上方有图片上传区域，支持拖拽或点击选择文件。支持的格式包括 `.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`、`.svg`、`.bmp`，单个文件不超过 16 MB。

上传完成后，页面会显示对应的 Markdown 引用代码（如 `![photo.png](/images/photo.png)`），点击即可复制，粘贴到编辑器中使用。文件名重复时系统会自动追加时间戳。

### 一键部署

点击导航栏的「部署上线」按钮并确认后，系统依次执行：

1. `hexo clean` — 清理旧的生成文件和缓存
2. `hexo generate` — 将 Markdown 渲染为 HTML
3. `hexo deploy` — 将静态文件推送到 GitHub Pages

页面底部会弹出日志面板，实时显示命令输出。部署过程中按钮自动禁用，完成后恢复。

部署成功后，GitHub Pages 通常需要 1–2 分钟完成 CDN 刷新，之后访问 [https://carbohydrate1001.github.io](https://carbohydrate1001.github.io) 即可看到更新。

---

## 在另一台电脑上使用

无论以哪种方式运行管理器，新电脑上都需要安装 Node.js、Git、Hexo CLI，并配置好 SSH Key。如果使用脚本模式，还需要 Python 和 Flask。

迁移步骤很简单：

1. 将 `carbospace/` 整个文件夹复制到新电脑。
2. 在 `carbospace/` 目录下执行 `npm install`，安装 Node.js 依赖。`node_modules/` 体积较大，不建议直接复制，通过 `package.json` 自动安装即可。
3. 启动管理器。

可以用以下命令确认环境是否就绪：

```bash
node -v                # Node.js
git --version          # Git
hexo version           # Hexo CLI
ssh -T git@github.com  # SSH 连接（应显示 "Hi Carbohydrate1001!"）
```

---

## 项目结构

```
carbospace/
├── blog_manager/
│   ├── app.py                     # Flask 主应用
│   ├── requirements.txt           # Python 依赖
│   ├── build.spec                 # PyInstaller 打包配置
│   ├── build.bat                  # 打包脚本（Windows）
│   ├── templates/                 # HTML 模板
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── editor.html
│   │   └── preview.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── source/
│   ├── _posts/                    # 文章 Markdown 文件
│   └── images/                    # 上传的图片
├── themes/next/                   # NexT 主题
├── _config.yml                    # Hexo 主配置
├── package.json                   # Node.js 依赖
└── USAGE_GUIDE.md                 # Hexo 博客使用手册
```

---

## API 参考

管理器提供以下 HTTP 端点，日常使用通过界面操作即可，也可直接调用：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 仪表盘，列出所有文章 |
| GET/POST | `/new` | 新建文章 |
| GET/POST | `/edit/<filename>` | 编辑文章 |
| POST | `/delete/<filename>` | 删除文章 |
| GET | `/preview/<filename>` | Markdown 预览 |
| POST | `/upload` | 上传图片 |
| GET | `/images/<filename>` | 访问已上传的图片 |
| GET | `/api/images` | 获取图片列表（JSON） |
| POST | `/deploy` | 触发部署 |
| GET | `/deploy/stream` | SSE 流式部署日志 |
| GET | `/deploy/status` | 查询部署状态 |

---

## 常见问题

**启动时报错 "Hexo project directory not found"**

管理器无法定位 `_config.yml`。确保 `blog_manager/` 位于 `carbospace/` 下（管理器向上级搜索），或通过 `--project-dir` 参数手动指定路径。

**部署失败**

常见原因有三个：hexo 未安装（执行 `npm install -g hexo-cli`）、SSH Key 未配置（执行 `ssh -T git@github.com` 检查）、`node_modules` 缺失（在 `carbospace/` 下执行 `npm install`）。

**上传图片后预览中看不到**

确认 Markdown 中的图片路径格式为 `![alt](/images/filename.png)`。上传成功后系统会自动生成正确格式，复制粘贴即可。

**部署后网站样式丢失**

检查 `_config.yml` 中 `url` 字段是否正确：

```yaml
url: https://carbohydrate1001.github.io
```

修改后重新部署。

**端口 5000 被占用**

修改 `app.py` 末尾的端口号，例如改为 `8080`：

```python
app.run(host='127.0.0.1', port=8080, debug=False)
```

**打包后模板或样式加载失败**

请使用项目提供的 `build.spec` 打包，不要直接执行 `pyinstaller app.py`。正确方式为在 `blog_manager/` 下运行 `build.bat`。

**编辑器或预览页面加载缓慢**

EasyMDE、marked.js 和 highlight.js 通过 CDN 加载，首次访问时可能较慢，浏览器缓存后会明显改善。长期离线环境下，可将这些库下载到 `static/` 目录改为本地加载。
