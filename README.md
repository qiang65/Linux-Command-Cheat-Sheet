# Linux 手册 · 离线单机版

> **想基于这套架构做别的程序？** 见 [docs/开发指引.md](docs/开发指引.md)（架构说明、10 步移植清单、Qt 陷阱清单、测试纪律）。

一个可独立运行的 Linux 知识手册程序：顶部横向分类页 + 左侧纵向分组词条列表 + 右侧详情，
全部内容存放在本地 SQLite 数据库，支持新增、编辑、删除、收藏与全文搜索。

界面风格参考菜鸟教程（runoob.com）的手册页布局，做了现代化处理：卡片式详情、
圆角控件、代码块一键复制、浅色/深色双主题。

## 运行

```bash
./launcher.sh              # 推荐：带依赖自检
python3 app.py             # 直接运行
python3 app.py --rebuild   # 清空并重新灌入初始数据
python3 app.py --db /路径/自定义.db   # 使用指定数据库
```

依赖：Python 3 + PyQt5。Windows/macOS 可在项目目录运行：

```bash
python -m pip install -r requirements.txt
```

Linux 也可使用系统包管理器安装：

```bash
sudo apt install python3-pyqt5
```

## Windows 与 macOS

Windows 构建单文件程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

构建产物为 `dist/LinuxManual.exe`。首次运行时数据库保存在当前用户的应用数据目录。

macOS 可双击 `启动Linux手册.command`。首次运行会创建 `.venv-macos` 并安装 PyQt5，之后直接启动程序。若 macOS 阻止脚本运行，在终端进入项目目录执行一次：

```bash
chmod +x 启动Linux手册.command
```

macOS 脚本需要项目文件夹完整保留，并需要 Python 3；首次安装依赖需要网络。原生 `.app` 需要在 macOS 上另行构建，本 Windows 构建脚本只生成 Windows exe。

桌面启动图标：

```bash
./install.sh               # 写入 ~/.local/share/applications，可在应用菜单里搜索「Linux 手册」
```

## 界面结构

```
┌──────────────────────────────────────────────────────────────────┐
│ ▣ Linux 手册  ◀[速查表][Shell教程][参考手册]▶  搜索  ＋新增 ⚙ ☾  │
├────────────────────┬─────────────────────────────────────────────┤
│ 纵向词条列表        │  词条详情                                     │
│ ▸ 一、文件与目录操作 │  标题 · 分类标签 · 浏览次数                    │
│ ▸ 二、文件内容查看   │  摘要 / ⚠️ 风险提示                            │
│ ▸ 三、…            │  代码卡片（右上角「复制」一键进剪贴板）         │
│  默认全部收起       │  [☆收藏] [编辑] [删除]                        │
│  点标题才展开       │                                             │
│  名称过长悬停跑马灯  │  [展开/收起图标] [收藏图标]                    │
├────────────────────┴─────────────────────────────────────────────┤
│ 状态栏：分类 › 分组 › 词条 · 浏览次数                                │
└──────────────────────────────────────────────────────────────────┘
```

- **横向分类栏**：Linux 命令速查表 / Shell 教程 / Linux 参考手册（可在设置页自行增删），
  两侧带 `◀ ▶` 箭头按钮，分类多时横向滚动翻看，不会挤压搜索框；**设置**不占用分类位，
  抽到右上角齿轮图标
- **顶部分类按钮互斥高亮**：同一时刻只有一个分类是亮色（绿底白字），点哪个哪个亮、
  其余变暗，亮着的分类就是左侧纵向栏显示的内容；进入「设置」时所有分类按钮都熄灭
- **点一栏** → 左侧显示该分类的分组标题，**默认全部收起**，点标题展开该组、再点收起
- 列表右上角是**两个 30px 图标按钮**（悬停显示文字）：展开/收起全部（一个按钮切换）、只看收藏
- 分组名、命令名过长时**鼠标停留自动跑马灯滚动**显示全文，移开复位
- 顶部分类栏可用**鼠标滚轮左右翻看**
- **点词条** → 右侧显示详情，长正文自动出现滚动条
- **单实例**：重复启动会自动把已打开的窗口唤醒到前台，不会开第二个窗口
- 窗口大小、位置、上次所在分类、主题、字号都会记忆

> 图标全部由 QPainter 自绘（`src/icons.py`），不使用 emoji 字符：本机只有位图版
> Noto Color Emoji，Qt5 渲染不出彩色字形，emoji 会显示成残缺方框。
>
> 命令名的字号与粗体用 `setFont` 显式设置，不走 QSS 的 `font-weight`：QSS 设粗体时
> QLabel 的 `sizeHint` 仍按非粗体计算，粗体实际更宽，末尾字符会被切掉半截。

## 快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl+F` | 聚焦搜索框（全文检索命令、参数、正文） |
| `Ctrl+N` | 新增词条 |
| `Ctrl+R` | 切换浅色 / 深色主题 |
| `Ctrl+1 ~ 9` | 直接切换横向分类页 |
| `Ctrl+0` | 打开设置页 |
| `Esc` | 清空搜索条件 |

## 数据

数据库：`data/linux.db`（SQLite，WAL 模式）

| 表 | 作用 |
| --- | --- |
| `categories` | 横向分类页（可在设置页增删改） |
| `groups` | 词条分组（章节），可增删改名 |
| `entries` | 词条：名称、摘要、参数、示例、注意、标签、正文、收藏标记、浏览次数 |
| `history` | 最近浏览记录（保留 500 条） |
| `trash` | 删除记录：词条完整快照 + 删除时间（保留 200 条），可逐条恢复 |
| `settings` | 主题、字号、窗口位置、上次分类 |

初始数据 **690 条词条 / 45 个分组 / 5 个分类**：

- **Linux 命令速查表**：168 条，14 个分组，来自本地《Linux 命令速查表.md》
- **Linux 命令大全**：441 条，11 个分组（文件管理 / 文档编辑 / 文件传输 / 磁盘管理 /
  磁盘维护 / 网络通讯 / 系统管理 / 系统设置 / 备份压缩 / 设备管理 / 其他命令），
  来自 runoob.com《Linux 命令大全》逐条命令页，含**说明、语法、参数、实例**
- **Shell 教程**：12 条，来自 runoob.com Shell 板块（变量、参数、数组、运算符、
  test、流程控制、函数、重定向、文件包含、echo/printf）
- **Docker 命令**：54 条，9 个分组（容器生命周期管理 / 容器操作 / rootfs / 镜像仓库 /
  本地镜像管理 / info|version / Docker Compose / 网络命令 / 卷命令），来自 runoob.com
  《Docker 命令大全》，含**说明、语法、选项、实例**
- **Linux 参考手册**：15 条，来自 runoob.com Linux 板块（简介、安装、启动过程、
  目录结构、WSL、云服务器、文件属性、目录管理、远程登录、忘记密码、用户与组、
  磁盘管理、yum、apt、vi/vim）

> 《Linux 命令大全》数据源是页面动态加载的
> `wp-content/themes/runoob/assets/linux-command-data.json`（11 分类 / 441 命令），
> 抓取脚本 `tools/build_comm_manual.py` 逐页抓取详情页，缓存在 `.cache/comm/`，
> 重跑不再联网。其中 `docker / podman / kubectl / virsh` 四个命令页在 runoob 上
> 已 404，这 4 条保留一句话说明。

字段约定：速查表词条只有一句说明，存在 `summary`，`content` 留空；教程类词条
`summary` 是首段摘要，`content` 是完整正文。详情页会自动识别两者重叠并只渲染一次，
所以同一段说明不会显示两遍。

设置页可**导出 JSON 备份**、**导入 JSON（合并/覆盖）**、**恢复初始数据**。

## 增删改词条

- 右上「＋ 新增词条」或 `Ctrl+N`
- 详情页「编辑」修改任意字段，「删除」移除词条
- 「分组」下拉框可直接输入新分组名，保存时自动创建
- 「☆ 收藏」给词条加 ★，勾选「★ 只看收藏」可单独浏览常用命令

## 删除保护与删除记录

- 删除词条需**两步确认**（第 1 步确认对象，第 2 步确认移入删除记录）
- 删除后词条完整快照进入 `trash` 表，设置页「删除记录」列出最近 200 条
- 点击记录里的「↩ 恢复」即还原到原分类原分组；若原分类已被删除，会自动补建该分类
- 「清空删除记录」需确认，清空后不可恢复

## 分类管理（扩展知识库）

设置页「分类管理」可：

- **添加分类**：输入名称（如 `Docker 速查`、`网络排查`）→ 立即出现在顶部横向页
- **拖拽排序**：按住某一行拖动即可改变分类顺序，松手即写库，顶部横向页**立即同步**，
  高亮分类与纵向栏保持对应，重启后顺序不变
- **重命名**分类
- **删除**分类：两步确认，其下词条全部进入删除记录，可逐条恢复
- 内置的「设置」分类不可删除

顶部分类栏支持**鼠标滚轮左右翻看**（也可点两侧 `◀ ▶` 箭头）。

新分类建好后，用「＋ 新增词条」选该分类录入，或用「导入 JSON」批量灌入
（JSON 结构见 `data/seed.json`：`categories[].groups[].entries[]`）。

## 目录结构

```
app.py                启动入口（单实例锁、自动建库灌种子）
launcher.sh           启动脚本（依赖自检）
install.sh            安装桌面启动图标
src/db.py             数据层：建库、增删改查、搜索、收藏、历史、导入导出
src/main_window.py    主窗口：顶部横向页 + 纵向分组列表 + 详情
src/icons.py          QPainter 自绘矢量图标（齿轮 / 月牙 / 太阳 / 箭头 / 加号 / logo）
src/marquee.py        跑马灯标签（文字超宽时悬停滚动显示）
src/markdown_view.py  正文渲染：标题/列表/表格/代码卡片（含复制按钮）
src/theme.py          浅色 / 深色主题与全局样式
src/editor.py         词条编辑对话框
src/settings_page.py  设置页
tools/build_seed.py   抓取 runoob 页面 + 解析本地速查表 → data/seed.json
tools/build_comm_manual.py 抓取《Linux 命令大全》441 个命令详情页 → data/comm_seed.json
tools/build_docker_manual.py 抓取《Docker 命令大全》54 个命令 → data/docker_seed.json
tools/merge_seed.py   把生成的种子片段合并进 data/seed.json
tools/html2md.py      正文 HTML → Markdown 解析器
tools/smoke_test.py   离屏冒烟测试（自动截图到 .shots/）
tools/layout_check.py 布局体检（检查控件尺寸、搜索、折叠、主题）
tools/e2e_test.py     端到端验收（增删改、导入导出、收藏、复制、持久化）
tools/feature_test.py 功能验收（分组折叠、命令名显示、删除记录恢复、分类管理）
tools/ui_check.py     顶部栏验收（矢量图标渲染、箭头滚动分类栏、设置按钮抽出）
tools/theme_drag_test.py 深色配色（真实像素采样）、滚轮翻分类、拖拽排序、跑马灯
tools/docker_test.py      《Docker 命令》导入验收（9 组、章节切分、代码卡片、搜索）
tools/coverage_check.py 渲染覆盖率检查（详情页文字量 / 词条原文量，查内容不全）
tools/drag_test.py     拖放排序全链路（拖放→写库→tabBar 同步→高亮对应→重启持久化）
tools/tab_test.py     分类按钮互斥高亮验收（高亮唯一且与纵向栏一致、键盘/增删/排序后跟随）
tools/comm_manual_test.py  《Linux 命令大全》441 条导入验收（分类、分组、详情、搜索、404 兜底）
tools/font_check.py   纵向列表命令名切字检查（逐条比对文字宽度与控件宽度）
tools/dup_check.py    详情页重复渲染检查
tools/live_shots.py   真实 X11 环境渲染截图
data/seed.json        初始种子数据
docs/开发指引.md      ★ 复用这套架构开发其他程序的完整指引
data/linux.db         运行数据库（首次运行自动生成）
```

## 重新抓取 / 更新内容

```bash
python3 tools/build_seed.py "Linux 命令速查表.md"   # 重新生成 data/seed.json
python3 tools/build_comm_manual.py                   # 抓取《Linux 命令大全》441 页
python3 tools/merge_seed.py data/comm_seed.json data/docker_seed.json   # 合并进 seed.json
python3 app.py --rebuild                             # 用新种子重建数据库
```

抓取脚本带本地缓存（`.cache/`），已抓过的页面不会重复请求。

## 说明

- 程序完全离线运行，除首次抓取种子数据外不需要网络。
- Shell 教程与参考手册内容取自菜鸟教程公开页面，仅作个人学习整理使用。
