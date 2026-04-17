# 刷题网站（Flask）

一个基于 PDF 的刷题与学习平台，支持账号体系、双语界面（中文/English）、题库筛选刷题、学习备注，以及小游戏排行榜。

---

## 功能概览

### 1) 入口主页（Portal）
- 登录后默认进入入口页：`/`
- 模块入口：
  - 练一练（题库刷题）
  - 聊一聊（预留）
  - 玩一玩（2048 / 数独 / 俄罗斯方块）
  - 学一学（预留）

### 2) 题库刷题（Practice）
- 四级筛选：科目 / 章节 / 主题 / 年份
- 题目、答案、考纲三视图切换
- 完成状态、收藏状态、备注
- PDF 页面内预览

### 3) 小游戏与排行榜（Games）
- 游戏中心：`/games`
- 游戏页：`/games/<game_name>`
  - `2048`
  - `sudoku`
  - `tetris`
- 排行榜按每位用户在该游戏的**最高分**展示

### 4) 账号与用户资料
- 注册 / 登录 / 退出
- 注册信息：用户名、密码、出生日期、学校、邮箱
- 密码哈希存储（Werkzeug）

### 5) 多语言支持
- 中文 / 英文切换
- 语言状态通过 `lang` 参数与 session 维持

---

## 技术栈

- Python 3.10+
- Flask
- Pandas
- SQLite

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

默认地址：<http://127.0.0.1:8000>

---

## 主要路由

### 鉴权
- `GET/POST /register`：注册
- `GET/POST /login`：登录
- `POST /logout`：退出

### 页面
- `GET /`：入口主页（需登录）
- `GET /practice`：刷题页（需登录）
- `GET /games`：游戏中心（需登录）
- `GET /games/<game_name>`：单个游戏页（需登录）

### 刷题相关
- `GET /pdfs/<path:filename>`：PDF 访问（需登录）
- `POST /toggle/<qid>/<field>`：切换完成/收藏（需登录）
- `POST /note/<qid>`：保存备注（需登录）

### 游戏相关 API
- `POST /api/games/<game_name>/score`：提交分数并返回最新排行榜（需登录）

---

## 数据与文件说明

- `app.db`
  - `users`：用户账号与资料
  - `game_scores`：游戏分数记录
- `progress_web.json`：按用户名隔离的刷题进度（done/favorite/note）
- `index.csv` / `index.xlsx`：题目索引
- `pdfs/`：题目、答案、考纲 PDF 文件

---

## 部署注意事项

1. **必须设置环境变量 `SECRET_KEY`**
2. 生产环境请关闭 Flask `debug=True`
3. 若模板报 `BuildError: Could not build url for endpoint 'portal'`：
   - 通常是服务器还在跑旧代码/旧进程
   - 请确认部署版本已包含 `portal` 路由并重启服务
4. 建议用 Gunicorn/uWSGI + Nginx 进行生产部署

---

## 目录结构（简化）

```text
.
├── app.py
├── requirements.txt
├── README.md
├── index.csv
├── app.db                  # 运行后生成
├── progress_web.json
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── portal.html
│   ├── index.html          # /practice
│   ├── games_home.html
│   └── game_play.html
└── pdfs/
```

---

## 后续可扩展建议

- 聊一聊（论坛）模块接入数据库与帖子/评论系统
- 学一学（资料中心）接入可视化资源管理
- 游戏排行榜增加：日榜/周榜、分页、反作弊
- 题库进度从 JSON 迁移到 SQLite（便于统计与扩展）
