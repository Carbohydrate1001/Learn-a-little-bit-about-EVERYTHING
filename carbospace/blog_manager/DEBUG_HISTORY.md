# CarboBlogManager Debug History

记录项目开发与维护过程中遇到并解决的 bug。

---

## Version 1.0 开发日志

**发布日期**：2026-03-02

Version 1.0 完成了 CarboBlogManager 的核心功能搭建，包括：

- 基于 Flask 的 Web 管理界面，支持博客文章的新建、编辑、删除和预览
- 集成 EasyMDE Markdown 编辑器，提供实时预览与语法高亮
- 图片拖拽上传功能，自动插入 Markdown 图片引用
- 一键部署（hexo clean → hexo generate → hexo deploy），通过 SSE 实时推送部署日志
- 支持通过 PyInstaller 打包为单文件可执行程序，方便在无 Python 环境的机器上使用

---

## Version 1.1 维护日志

**日期**：2026-03-02 ~ 2026-03-03

Version 1.0 上线后发现并修复了以下问题：

---

### Bug #001：CRLF 双写导致文件损坏

**发现日期**：2026-03-02

**现象**：
- 通过管理器保存或新建的文章，部署到 GitHub Pages 后标题显示为 "Untitled"
- 文章详情页开头显示原始 YAML front-matter 文本（`title: ...`, `date: ...`, `tags: ...`）
- 文章日期回退为文件修改时间而非 front-matter 中指定的日期
- 部署看起来有"一步延迟"——每次部署后看到的是上一次的内容

**根因**：
浏览器表单提交的内容使用 `\r\n`（CRLF）行尾。Python 在 Windows 上以文本模式 `open(..., 'w')` 写入时，会将所有 `\n` 自动转换为 `\r\n`。这导致原始内容中的 `\r\n` 变为 `\r\r\n`，在文件中表现为每行之间多出一个空行。

Hexo（Node.js）读取文件时不做行尾转换，双空行破坏了 YAML front-matter 的解析，使 Hexo 无法识别 `title`、`date` 等元数据。

**诊断证据**（运行时日志）：
```
edit_post:POST — saved_hash ≠ readback_hash, match: false
last_80_chars 中包含 \r\n 行尾
hexo generate 后 Road-to-LLM 日期路径为 2026/03/02（应为 2025/12/17）
```

**修复**：
在 `edit_post()` 和 `new_post()` 中，写入文件前规范化行尾：
```python
content = content.replace('\r\n', '\n').replace('\r', '\n')
with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
```
- `.replace('\r\n', '\n')` 消除浏览器带来的 CRLF
- `newline='\n'` 阻止 Python 在 Windows 上的自动行尾转换

**影响范围**：`app.py` 中的 `edit_post()`、`new_post()`

**验证**：修复后日志显示 `saved_hash == readback_hash, match: true`，hexo generate 路径恢复正确。

---

### Bug #002：源文件被 CRLF bug 损坏

**发现日期**：2026-03-02

**现象**：
- `Road-to-LLM.md` front-matter 行间有多余空行
- `test.md` 全文双空行
- `hello-world.md` 被误删
- `CarboBlogManager-使用手册.md` 通过旧版 Flask 实例保存后同样损坏

**根因**：Bug #001 的连锁影响。在代码修复部署到磁盘后，正在运行的 Flask 进程仍使用内存中的旧代码，导致新文章继续被损坏写入。

**修复**：手动重写所有损坏的源文件，恢复正确的 front-matter 格式和内容。

**经验**：修改 `app.py` 后必须重启 Flask 应用（Ctrl+C 后重新 `python app.py`），否则代码修改不会生效。

---

### Bug #003：UnicodeEncodeError（GBK 编码）

**发现日期**：2026-03-02

**现象**：Flask 应用启动时，控制台输出包含 emoji 的 print 语句触发 `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680'`。

**根因**：Windows 控制台默认使用 GBK 编码，无法显示 emoji 字符。

**修复**：移除 `app.py` 中 print 语句里的 emoji 字符。

---

### 非 Bug：GitHub Pages CDN 延迟

**记录日期**：2026-03-03

**现象**：`hexo deploy` 成功后，GitHub Pages 上的内容没有立即更新，通常需要 1–2 分钟才能看到最新版本。不同页面（首页、归档、文章详情）的更新速度可能不一致。

**原因**：这是 GitHub Pages 基础设施的正常行为。部署推送到仓库后，GitHub 需要触发 Actions 构建流水线并刷新全球 CDN 节点缓存。

**处理方式**：非代码问题，无需修复。部署后等待 1–2 分钟，用 Ctrl+Shift+R 强制刷新浏览器即可。
