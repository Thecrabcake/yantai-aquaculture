# 烟台海产养殖行情助手（一期）

帮海阳养殖朋友做的手机行情工具：看走势、估出虾价格区间、读行业新闻、算保本价、新手避坑。

**形态**：纯静态站点（SQLite → HTML，ECharts 本地化，无后端无 CDN），开发电脑上跑两条命令更新，手机同一 WiFi 访问。

## 页面清单

| 页面 | 功能 |
|---|---|
| index.html | 行情看板：6 个 tab 价格曲线（春节/中秋标注）+ 暖水虾进口柱状图 |
| forecast.html | 出虾价格区间预测：输入出虾窗口 → 历史中位价/常规区间/分年对比/情景修正 |
| news.html | 行业新闻：病害/进口/政策/天气四类，人工周选 |
| cost.html | 保本价计算器：投入 → 预计产量/总成本/保本价 |
| guide.html | 新手手册：一年时间轴 + 三板块要点 + 10 条避坑清单 |
| 月报-YYYY-MM.html | 月报一页纸（generate 命令生成，可微信转发） |

## 更新命令（详见 docs/维护手册.md）

```bash
cd yantai-aquaculture
# 1. 更新数据（抓月报 + 读录入档，幂等）
PYTHONPATH=src python -c "from aqua import pipeline; pipeline.run('data/aquarium.db', csv_dir='data')"
# 2. 重新生成站点
PYTHONPATH=src python -c "from aqua.web import build; build.build('data/aquarium.db', 'site')"
# 3. 生成当月月报
PYTHONPATH=src python -c "from aqua.web import report; report.generate('data/aquarium.db', '2026-09', 'site')"
# 手机访问：python -m http.server 8000 --directory site
```

## 目录结构

```
src/aqua/
├── db.py            # SQLite 数据层（price/import_stat/news 三表）
├── normalize.py     # 物种/日期/价格单位标准化
├── forecast.py      # 出虾窗口统计（给区间不给点）
├── costcalc.py      # 成本模型
├── pipeline.py      # 全流程：各源 → 库 → CSV 备份
├── newsman.py       # 人工新闻周选导入（去重）
├── sources/         # moa（月报大类价+进口）、customs（人工月录）、huinong（惠农网生蚝每日价）、fishfirst（水产频道历史回填）、manual_price（人工周录）
└── web/             # build（站点生成）、report（月报）、templates（5+1 模板）
data/                # 录入档（import_manual/price_manual/news_manual）、aquarium.db、price.csv
site/                # 构建产物（不提交）
docs/                # 设计/计划/维护手册/验收清单
```

## 已知数据缺口（如实告知）

1. **品种级价格**来源：生蚝=惠农网每日产地价（自动）；白虾=水产频道 2022-2024 历史点（回填）；皮皮虾/梭子蟹=市场报道历史点+人工周录。2025 年后周度行情无公开可爬源，仍靠周录攒，前几月数据稀疏；历史曲线主力是**大类**（虾蟹类/贝类，农业农村部月报，2023-10 起）
2. **暖水虾进口量**为人工月度录入（海关需交互查询）
3. **口径差**：页面是全国批发市场价，与海阳当地成交价有价差（记账模块二期用真实成交价校准）
4. 月报月均价受月度数据滞后影响（当月报滞后 1-2 月）
