# 刷题网站（Flask）

一个基于 PDF 的刷题与学习平台，支持账号体系、双语界面、题库筛选刷题、学习备注、小游戏排行榜，以及学习/编程/履历子页面。

## 模块说明

- 入口页 `/`
  - 学一学：进入学习子页面（看课件 / 看动画 / 看文章）
  - 练一练：题库筛选 + PDF 阅读
  - 编一编：CAIE Pseudocode IDE（可运行伪代码 + 显示官方PDF指南）
  - 支持：DECLARE、INPUT、FOR/TO/NEXT（含 NEXT i）、IF/ELSE、CASE、WHILE、REPEAT、PROCEDURE/FUNCTION/CALL/RETURN、MIDSTRING、RAND
  - 规则：变量与数组必须先 DECLARE，未声明即报错
  - 输入可在编一编页面按行提供（对应 INPUT）
  - 玩一玩：小游戏中心
  - 拜一拜：个人履历展示页

- 游戏 `/games`
  - 仅保留：`2048`、`tetris`、`nonogram`、`sudoku`、`minesweeper`、`hanoi`
  - 每个游戏支持排行榜（2048/俄罗斯方块按分数高到低；数独/数织/扫雷/汉诺塔按用时短到长）
  - 数织固定为 `8*8`
  - 数织与数独在通关后会自动随机生成下一题
  - 扫雷固定 16x30，99 雷
  - 汉诺塔固定 5 个盘子

- 刷题 `/practice`
  - 四级筛选：科目 / 章节 / 主题 / 年份
  - 左侧题目列表滚动，右侧备注栏，中央 PDF 阅读器
  - PDF 支持全屏按钮

## 新增路由

- `GET /learn`：学一学子页面
- `GET /code`：编一编（伪代码 IDE）
- `POST /api/code/run`：执行伪代码
- `GET /profile`：拜一拜（个人履历）

## 快速启动

```bash
python app.py
```

默认地址：<http://127.0.0.1:8000>


## 文档放置路径

- 官方伪代码指南 PDF：`static/docs/caie-pseudocode-guide.pdf`


## 拜一拜（Cyber Blessing）

- 三个板块：赛博求签 / 赛博上香 / 赛博功德
- 今日上香人数按天统计
- 求签概率：A* 50%、A 30%、B 15%、C 5%
