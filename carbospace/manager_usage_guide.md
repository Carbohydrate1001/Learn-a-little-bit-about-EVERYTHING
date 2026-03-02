# CarboBlogManager 使用手册

> **CarboBlogManager** 是一个基于 Flask 的本地 Web 管理系统，专为 Carbospace Hexo 博客打造。
> 提供文章增删改查、Markdown 编辑预览、图片上传以及一键部署到 GitHub Pages 的功能。

---

## 目录

- [CarboBlogManager 使用手册](#carboblogmanager-使用手册)
  - [目录](#目录)
  - [一、环境要求](#一环境要求)
  - [二、启动方式](#二启动方式)
    - [方式 A：Python 脚本直接运行](#方式-apython-脚本直接运行)
    - [方式 B：打包为 .exe 可执行程序](#方式-b打包为-exe-可执行程序)
  - [三、功能说明](#三功能说明)
    - [3.1 仪表盘（文章列表）](#31-仪表盘文章列表)
    - [3.2 新建文章](#32-新建文章)
    - [3.3 编辑文章](#33-编辑文章)
    - [3.4 删除文章](#34-删除文章)
    - [3.5 Markdown 预览](#35-markdown-预览)
    - [3.6 图片上传](#36-图片上传)
    - [3.7 一键部署](#37-一键部署)
  - [四、在另一台电脑上使用](#四在另一台电脑上使用)
    - [4.1 前置环境](#41-前置环境)
    - [4.2 迁移步骤](#42-迁移步骤)
    - [4.3 环境检查清单](#43-环境检查清单)
  - [五、项目结构](#五项目结构)
  - [六、API 参考](#六api-参考)
  - [七、常见问题](#七常见问题)

---

## 一、环境要求

| 工具      | 最低版本 | 用途                    | 检查命令        |
| --------- | -------- | ----------------------- | --------------- |
| Python    | 3.8+     | 运行管理器（脚本模式）  | `python --version` |
| Node.js   | 14.x     | 运行 Hexo 命令          | `node -v`       |
| npm       | 6.x      | 管理 Hexo 依赖          | `npm -v`        |
| Git       | 2.x      | 部署推送到 GitHub       | `git --version` |
| Hexo CLI  | 4.x      | 执行 hexo 命令          | `hexo version`  |

**额外要求**：

- **SSH Key**：本机 SSH 公钥已添加到 GitHub 账户（部署通过 SSH 推送）
- **Hexo 依赖**：`carbospace/` 目录下已执行过 `npm install`（存在 `node_modules/`）

> 如果使用 .exe 模式运行，不需要安装 Python，但仍需要 Node.js、Git 和 Hexo CLI。

---

## 二、启动方式

### 方式 A：Python 脚本直接运行

```bash
# 1. 进入管理器目录
cd carbospace/blog_manager

# 2. 安装 Python 依赖（首次使用）
pip install flask

# 3. 启动管理器
python app.py
```

程序启动后会：
1. 自动检测上级目录中的 `_config.yml`，定位 Hexo 项目
2. 在 `http://localhost:5000` 启动 Web 服务
3. 自动打开默认浏览器进入管理页面

**手动指定项目路径**（当自动检测失败时）：

```bash
python app.py --project-dir "D:\path\to\carbospace"
```

### 方式 B：打包为 .exe 可执行程序

#### 打包步骤

```bash
# 1. 进入管理器目录
cd carbospace/blog_manager

# 2. 安装依赖（含 PyInstaller）
pip install -r requirements.txt

# 3. 执行打包脚本
build.bat
```

打包成功后，在 `dist/` 目录下生成 `CarboBlogManager.exe`。

#### 运行 .exe

**方法一**：将 `CarboBlogManager.exe` 放到 `carbospace/` 目录（或其子目录）下，双击运行。

**方法二**：在任意位置运行，通过参数指定项目路径：

```bash
CarboBlogManager.exe --project-dir "D:\path\to\carbospace"
```

---

## 三、功能说明

### 3.1 仪表盘（文章列表）

**访问路径**：`http://localhost:5000/`

仪表盘以卡片形式展示 `source/_posts/` 中所有 `.md` 文章，每张卡片显示：
- 文章标题
- 创建日期
- 标签列表
- 正文摘要（前 200 字）

**功能操作**：
- **搜索**：在搜索框输入关键词，实时过滤文章标题和标签
- **编辑**：点击卡片上的「编辑」按钮进入编辑器
- **预览**：点击「预览」按钮在新标签页查看渲染效果
- **删除**：点击「删除」按钮，确认后删除文章文件

### 3.2 新建文章

**访问路径**：`http://localhost:5000/new`（或点击导航栏「新建文章」）

新建文章页面包含：

| 字段   | 说明                                  | 示例                    |
| ------ | ------------------------------------- | ----------------------- |
| 标题   | 必填，同时作为文件名                  | `深度学习入门笔记`       |
| 标签   | 选填，多个标签用英文逗号分隔          | `Deep Learning, Python` |
| 分类   | 选填，多个分类用英文逗号分隔          | `技术笔记, AI`          |
| 正文   | 选填，Markdown 编辑器                 | 正文内容                |

点击「创建文章」后，系统会：
1. 自动生成 YAML Front-matter（包含 title、date、tags、categories）
2. 在 `source/_posts/` 下创建对应的 `.md` 文件
3. 跳转到编辑器页面继续编写

**生成的 Front-matter 示例**：

```yaml
---
title: 深度学习入门笔记
date: 2026-03-02 17:30:00
tags:
  - Deep Learning
  - Python
categories:
  - 技术笔记
  - AI
---
```

### 3.3 编辑文章

**访问路径**：`http://localhost:5000/edit/<filename>`

编辑器使用 **EasyMDE**（一个功能丰富的 Markdown 编辑器），提供：

- **工具栏**：粗体、斜体、删除线、标题、引用、列表、链接、图片、表格、代码块、水平线
- **实时预览**：点击工具栏的预览按钮，或使用分屏模式（Side by Side）
- **全屏模式**：专注写作
- **自动保存**：每 5 秒自动保存到浏览器本地存储（防止意外丢失）
- **状态栏**：显示行数、字数、光标位置

**注意**：编辑器中的内容包含完整的 Front-matter 和正文。修改 Front-matter 中的 title、tags 等字段会直接生效。

点击「保存」按钮将内容写入磁盘文件。

### 3.4 删除文章

在仪表盘中点击文章卡片上的「删除」按钮：

1. 弹出确认对话框，显示文章标题
2. 点击「确认删除」后，从 `source/_posts/` 中移除对应的 `.md` 文件
3. 返回仪表盘

> **注意**：此操作不可撤销。如果需要恢复，请使用 Git 版本历史。

### 3.5 Markdown 预览

**访问路径**：`http://localhost:5000/preview/<filename>`

独立的全页预览页面，使用 **marked.js** 渲染 Markdown 并通过 **highlight.js** 高亮代码块。

预览页面展示：
- 文章标题（大标题）
- 日期和标签
- 渲染后的正文内容（支持标题、列表、表格、代码块、图片、引用等）

页面顶部提供「返回列表」和「编辑此文章」的快捷按钮。

### 3.6 图片上传

在编辑文章页面，编辑器上方有一个**图片上传区域**：

**上传方式**：
- **拖拽上传**：将图片文件拖拽到上传区域
- **点击上传**：点击「点击选择文件」链接选择图片

**支持的格式**：`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`、`.svg`、`.bmp`

**上传大小限制**：单个文件最大 16 MB

**上传流程**：
1. 选择或拖入图片文件
2. 图片自动保存到 `source/images/` 目录
3. 上传成功后显示 Markdown 引用代码，例如：`![photo.png](/images/photo.png)`
4. 点击引用代码即可复制到剪贴板
5. 在编辑器中粘贴即可插入图片

> 如果文件名重复，系统会自动在文件名后追加时间戳，避免覆盖已有文件。

### 3.7 一键部署

点击导航栏右侧的「部署上线」按钮：

1. 弹出确认对话框
2. 确认后，系统依次执行以下命令：
   - `hexo clean` — 清理之前生成的静态文件和缓存
   - `hexo generate` — 将 Markdown 渲染为 HTML 静态文件
   - `hexo deploy` — 将静态文件推送到 GitHub Pages
3. 页面底部弹出**部署日志面板**，实时显示命令输出
4. 部署完成后显示成功或失败状态

**部署成功后**，等待 1-2 分钟，访问 [https://carbohydrate1001.github.io](https://carbohydrate1001.github.io) 即可查看更新后的博客。

> **提示**：部署过程中按钮会自动禁用，防止重复操作。部署完成后恢复可用。

---

## 四、在另一台电脑上使用

### 4.1 前置环境

无论使用哪种方式运行管理器，新电脑必须安装以下工具（因为部署依赖 `hexo` 命令）：

| 工具      | 安装方式                                        |
| --------- | ----------------------------------------------- |
| Node.js   | [https://nodejs.org](https://nodejs.org) 下载   |
| Git       | [https://git-scm.com](https://git-scm.com) 下载 |
| Hexo CLI  | `npm install -g hexo-cli`                       |
| SSH Key   | `ssh-keygen -t rsa -C "your@email.com"`，将公钥添加到 GitHub |

如果使用 Python 脚本模式，还需要安装 **Python 3.8+** 和 **Flask**。

### 4.2 迁移步骤

**步骤 1**：将 `carbospace/` 整个项目文件夹复制到新电脑（U 盘、网盘、Git 均可）。

**步骤 2**：在新电脑的 `carbospace/` 目录下安装 Node.js 依赖：

```bash
cd carbospace
npm install
```

> `node_modules/` 目录通常有上百 MB，不建议直接复制，用 `npm install` 根据 `package.json` 自动安装即可。

**步骤 3**：启动管理器。

使用 .exe（推荐）：

```bash
# 将 CarboBlogManager.exe 放到 carbospace/ 目录下
# 双击运行

# 或在任意位置通过参数指定：
CarboBlogManager.exe --project-dir "D:\path\to\carbospace"
```

使用 Python 脚本：

```bash
cd carbospace/blog_manager
pip install flask
python app.py
```

### 4.3 环境检查清单

在新电脑上运行以下命令，全部通过后即可使用管理器：

```bash
node -v                # 确认 Node.js 已安装
git --version          # 确认 Git 已安装
hexo version           # 确认 Hexo CLI 已安装
ssh -T git@github.com  # 确认 SSH 连接正常（应显示 "Hi Carbohydrate1001!"）
```

---

## 五、项目结构

```
carbospace/
├── blog_manager/                  # 管理器应用
│   ├── app.py                     #   Flask 主应用（路由、API、部署逻辑）
│   ├── requirements.txt           #   Python 依赖
│   ├── build.spec                 #   PyInstaller 打包配置
│   ├── build.bat                  #   一键打包脚本（Windows）
│   ├── templates/                 #   HTML 模板
│   │   ├── base.html              #     基础布局（导航栏、暗色主题）
│   │   ├── index.html             #     仪表盘（文章列表）
│   │   ├── editor.html            #     文章编辑器
│   │   └── preview.html           #     Markdown 预览
│   └── static/                    #   静态资源
│       ├── css/style.css          #     暗色主题样式
│       └── js/app.js              #     前端交互逻辑
├── source/
│   ├── _posts/                    #   文章 Markdown 文件（管理器读写此目录）
│   └── images/                    #   上传的图片（管理器写入此目录）
├── scaffolds/                     #   文章模板
├── themes/next/                   #   NexT 主题
├── _config.yml                    #   Hexo 主配置（管理器据此定位项目）
├── package.json                   #   Node.js 依赖清单
└── USAGE_GUIDE.md                 #   Hexo 博客使用手册
```

---

## 六、API 参考

管理器提供以下 HTTP 端点，在浏览器中通过界面操作，也可直接调用：

| 方法   | 路径                      | 说明                         |
| ------ | ------------------------- | ---------------------------- |
| GET    | `/`                       | 仪表盘，列出所有文章         |
| GET    | `/new`                    | 新建文章页面                 |
| POST   | `/new`                    | 创建新文章                   |
| GET    | `/edit/<filename>`        | 编辑文章页面                 |
| POST   | `/edit/<filename>`        | 保存文章修改                 |
| POST   | `/delete/<filename>`      | 删除文章                     |
| GET    | `/preview/<filename>`     | 文章 Markdown 预览           |
| POST   | `/upload`                 | 上传图片到 `source/images/`  |
| GET    | `/images/<filename>`      | 访问已上传的图片             |
| GET    | `/api/images`             | 获取所有已上传图片列表（JSON）|
| POST   | `/deploy`                 | 触发一键部署                 |
| GET    | `/deploy/stream`          | SSE 流式获取部署日志         |
| GET    | `/deploy/status`          | 查询当前部署状态             |

---

## 七、常见问题

### Q1：启动时报错 "Hexo project directory not found"

**原因**：管理器无法自动定位 `_config.yml` 文件。

**解决方案**：
- 确保 `blog_manager/` 位于 `carbospace/` 下（管理器会向上级搜索）
- 或使用参数手动指定：`python app.py --project-dir "D:\path\to\carbospace"`

### Q2：点击「部署上线」后报错

**可能原因**：
1. **hexo 未安装**：执行 `npm install -g hexo-cli`
2. **SSH Key 未配置**：执行 `ssh -T git@github.com` 检查
3. **node_modules 缺失**：在 `carbospace/` 下执行 `npm install`

### Q3：上传图片后在预览中看不到

**原因**：管理器在 `/images/<filename>` 路径下提供图片服务，但 Markdown 中引用的路径是 `/images/photo.png`。

**解决方案**：确保 Markdown 中的图片路径格式为 `![alt](/images/filename.png)`（上传成功后会自动生成正确格式，点击复制即可）。

### Q4：部署后网站样式丢失

**原因**：`_config.yml` 中的 `url` 配置不正确。

**解决方案**：确认 `_config.yml` 第 15 行：

```yaml
url: https://carbohydrate1001.github.io
```

然后重新部署。

### Q5：端口 5000 被占用

**解决方案**：修改 `app.py` 最后一行中的端口号：

```python
app.run(host='127.0.0.1', port=8080, debug=False)
```

或在使用 .exe 时，暂不支持自定义端口（需重新打包）。

### Q6：打包 .exe 后模板/样式加载失败

**原因**：PyInstaller 未正确打包 `templates/` 和 `static/` 资源。

**解决方案**：确保使用项目提供的 `build.spec` 进行打包（它已配置了 `--add-data`），不要直接使用 `pyinstaller app.py`。

正确的打包命令：

```bash
cd carbospace/blog_manager
build.bat
```

### Q7：EasyMDE 编辑器或预览页面加载缓慢

**原因**：编辑器（EasyMDE）和预览渲染库（marked.js、highlight.js）通过 CDN 加载，在网络不佳时可能较慢。

**解决方案**：首次加载后浏览器会缓存这些资源，后续访问会显著加快。如果长期处于离线环境，可以将这些库下载到 `static/` 目录下改为本地加载。
