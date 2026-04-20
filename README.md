# 刷题网站（Flask）

一个基于 PDF 的刷题与学习平台，支持账号体系、双语界面（中文/English）、题库筛选刷题、学习备注，以及多款小游戏积分排行榜。

## 功能概览

### 1) 入口主页（Portal）
- 登录后默认进入入口页：`/`
- 模块入口：
  - 练一练（题库刷题）
  - 玩一玩（游戏中心）
  - 学一学（预留）
  - 聊一聊（预留）
  - 编一编（伪代码编辑器预留）
  - 拜一拜（个人履历展示预留）

### 2) 题库刷题（Practice）
- 四级筛选：科目 / 章节 / 主题 / 年份
- 题目列表 + 中间 PDF 阅读器 + 右侧备注栏
- 左侧题目列表支持独立滚动
- 中间 PDF 阅读区加宽，默认按整页阅读（`page-fit`）
- 题目、答案、考纲三视图切换
- 完成状态、收藏状态、备注

### 3) 小游戏与排行榜（Games）
- 游戏中心：`/games`
- 每个游戏支持：
  - 难度切换（简单/普通/困难）
  - 按当前难度展示排行榜（每个用户最高分）
- 现有游戏：
  - 数织（Nonogram）
  - 扫雷
  - 汉诺塔
  - Dino
  - 打飞机
  - 华容道
  - 2048
  - 数独（保留）
  - 俄罗斯方块（保留）

### 4) 账号与用户资料
- 注册 / 登录 / 退出
- 注册信息：用户名、密码、出生日期、学校、邮箱
- 密码哈希存储（Werkzeug）

### 5) 多语言支持
- 中文 / 英文切换
- 语言状态通过 `lang` 参数与 session 维持

## 技术栈

- Python 3.10+
- Flask
- Pandas
- SQLite

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

默认地址：<http://127.0.0.1:8000>

## 主要路由

- `GET /`：入口主页（需登录）
- `GET /practice`：刷题页（需登录）
- `GET /games`：游戏中心（需登录）
- `GET /games/<game_name>`：单个游戏页（需登录）
- `POST /api/games/<game_name>/score`：提交分数并返回当前难度排行榜（需登录）

## 数据与文件说明

- `app.db`
  - `users`：用户账号与资料
  - `game_scores`：游戏分数记录（含 `difficulty` 字段）
- `progress_web.json`：按用户名隔离的刷题进度（done/favorite/note）
- `index.csv` / `index.xlsx`：题目索引
- `pdfs/`：题目、答案、考纲 PDF 文件

## 部署注意事项

1. 设置环境变量 `SECRET_KEY`
2. 生产环境关闭 Flask `debug=True`
3. 建议使用 Gunicorn/uWSGI + Nginx
