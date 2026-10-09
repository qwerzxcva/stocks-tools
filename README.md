# stocks-tools (股票项目管线脚本库)

## 用途
数据抓取 / 技术分析 / 监控 / 图表生成的工具脚本。不含任何数据。

## 目录
```
config/watchlist.txt     关注标的清单 (代码+英文名)
tools/
  fetch.sh               日常增量 (kline + snapshot + pools + moneyflow + news)
  fetch_history.py       A 股指数历史日线/周线/月线/年度统计
  fetch_capflow.sh       东财板块/个股资金流
  fetch_macro.sh         宏观报价 (美债/黄金/汇率)
  scan_market.py/sh      全市场快照
  scan_market_flow.sh    多日资金流
  news_collect.py/sh     7x24 新闻
  analyze_today.py       今日技术评分 + 可买/不可买报告
  monitor.py             盘中监控快照 (15 分钟循环)
  monitor_loop.sh        监控后台循环
  fetch_all_market.py    全市场 K 线批量采集 (WAF 退避, 断点续传)
  split_allmarket.py     把 collector 的 bulk shards 拆成按代码分文件
  global_aggregate.py    全球指数 K 线周/月/季/年聚合
  gen_stats.sh           情绪统计
  make_chart.sh          生成单只 K 线 SVG
  make_all_charts.sh     批量出图
  make_index.sh          生成 charts/index.html
  pick_hidden.py         低调潜力标的筛选
```

## 数据路径约定
- K 线输出 → `~/workspace/stocks-data-kline/data/`
- 快照/资金流 → `~/workspace/stocks-data-live/data/`
- 新闻 → `~/workspace/stocks-data-news/news/`
- 分析笔记 → `~/workspace/stocks/analysis/`
- 图表 → `~/workspace/stocks/charts/`

## 使用示例
```bash
# 日常增量
cd ~/workspace/stocks
bash tools/fetch.sh $(date +%Y-%m-%d)

# 盘中监控 (单次)
python3 tools/monitor.py $(date +%Y%m%d)

# 监控循环 (直到 15:10)
bash tools/monitor_loop.sh

# 全局 K 线采集 (耗时长)
python3 tools/fetch_all_market.py 2
```
