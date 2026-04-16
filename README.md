# 刷题网站（Flask）

一个基于 PDF 的刷题网站，支持四级筛选、题目/答案/考纲切换、做题进度、收藏和备注。

## 新增功能：用户鉴权 + 多用户进度隔离

- 使用 `SQLite` 存储账号信息（`app.db`）
- 支持自由注册、登录、退出
- 密码使用哈希存储（`werkzeug.security.generate_password_hash`）
- 题目进度仍然保存在 `progress_web.json`，但按用户名分区存储

示例：

```json
{
  "alice": {
    "Q001": {
      "done": true,
      "favorite": false,
      "note": "注意时间复杂度",
      "updated_at": "2026-04-16T12:00:00"
    }
  }
}
```

## 环境要求

- Python 3.10+

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动项目

```bash
python app.py
```

默认访问：<http://127.0.0.1:8000>

## 路由说明

- `GET/POST /register`：注册
- `GET/POST /login`：登录
- `POST /logout`：退出
- `GET /`：题库主页（需登录）
- `POST /toggle/<qid>/<field>`：切换完成/收藏（需登录）
- `POST /note/<qid>`：保存备注（需登录）

## 数据文件

- `app.db`：SQLite 用户表
- `progress_web.json`：用户进度数据
- `index.csv` / `index.xlsx`：题目索引数据

## 安全建议

- 生产环境请设置环境变量 `SECRET_KEY`
- 生产部署请关闭 Flask `debug` 模式
