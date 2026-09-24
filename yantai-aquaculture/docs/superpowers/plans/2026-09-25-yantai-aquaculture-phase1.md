# 烟台海产养殖行情助手 一期实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从公开数据源构建"行情看板 + 价格区间预测器 + 新闻 + 成本计算器 + 新手内容"的本地静态站点，供朋友手机浏览。

**Architecture:** Python 爬虫/整理脚本把多源数据标准化后写入 SQLite，构建脚本从 SQLite 生成纯静态 HTML 站点（ECharts 图表、无后端、无账号），本地电脑运行，浏览器/手机访问。

**Tech Stack:** Python 3.12 + SQLite（stdlib sqlite3）+ requests + beautifulsoup4 + pytest + ECharts 5（本地 vendor 的 echarts.min.js，不依赖 CDN）。

**Spec:** `docs/superpowers/specs/2026-09-25-yantai-aquaculture-design.md`

## 实施偏差记录（M1 完成时更新）

- **T3 moa 源**：实际测试契约断言大类 `虾蟹类`/`贝类` 而非 `白虾`——农业农村部月报只有大类均价，无单品种。品种级价格由 T5 补充。
- **T5 惠农网**：验证为 SPA 不可爬（数据 JS 渲染、无品种名），且不存在可爬的周度品种行情站。按计划降级路径实现为 `sources/manual_price.py`（人工周度录入 `data/price_manual.json`，同 customs 模式）。下方 T5 步骤中 `huinong` 均指 `manual_price`。

## Global Constraints

- Python 3.12（用户机器已装），新增依赖仅 requests / beautifulsoup4 / pytest
- 价格统一口径：**元/斤**（公斤价入库存前 ÷2）
- 物种名统一四值：`白虾` / `皮皮虾` / `梭子蟹` / `生蚝`
- 日期格式统一 `yyyy-mm-dd`（月度数据用 `yyyy-mm`）
- 页面手机优先（viewport、大字号、单列布局）
- 预测器只给区间和概率，页面必须带免责说明
- 无后端、无账号、无 CDN 依赖
- 注释和 commit 用中文；commit 格式 `类型: 简述`
- 单数据源失败不得拖垮整体管道（try/except + 告警日志继续）
- git 仓库为 `E:\ClaudeCode`（本计划所有 commit 均在该仓库根目录执行）

## 文件结构

```
yantai-aquaculture/
├── requirements.txt          # requests, beautifulsoup4, pytest
├── pytest.ini                # testpaths=tests, pythonpath=src
├── src/aqua/__init__.py
├── src/aqua/config.py        # 节假日表、情景修正系数、成本默认值
├── src/aqua/normalize.py     # 物种名/日期/单位标准化（纯函数）
├── src/aqua/db.py            # SQLite 建表与写入
├── src/aqua/forecast.py      # 出虾窗口价格统计（预测器核心计算）
├── src/aqua/costcalc.py      # 成本模型与保本价计算
├── src/aqua/newsman.py       # 人工新闻 JSON → 入库
├── src/aqua/pipeline.py      # 全流程入口：抓取→标准化→入库→备份CSV
├── src/aqua/sources/__init__.py
├── src/aqua/sources/base.py  # 抓取辅助：get/fixture 存取
├── src/aqua/sources/moa.py   # 农业农村部月度批发价
├── src/aqua/sources/customs.py  # 海关/行业口径月度进口量
├── src/aqua/sources/huinong.py  # 惠农网周度报价（含皮皮虾）
├── src/aqua/web/__init__.py
├── src/aqua/web/build.py     # SQLite → site/ 静态站点
├── src/aqua/web/report.py    # 月报一页纸生成
├── src/aqua/web/templates/{index,forecast,news,cost,guide}.html
├── fixtures/                 # 各数据源样本页（解析器测试用，入库跟踪）
├── data/                     # aquarium.db、CSV 备份、news_manual.json、import_manual.json
├── site/                     # 构建产物（gitignore）
└── tests/test_{normalize,db,forecast,costcalc,newsman,build}.py
```

模块依赖：`sources/*` → `normalize` → `pipeline` → `db`；`web/build` → `db` + `forecast` + `config`；`web/report` → `db` + `config`。

---

## 里程碑 M1：数据基础（T1-T6）

### Task 1: 项目骨架 + 数据库层

**Files:**
- Create: `yantai-aquaculture/requirements.txt`
- Create: `yantai-aquaculture/pytest.ini`
- Create: `yantai-aquaculture/src/aqua/__init__.py`（空文件）
- Create: `yantai-aquaculture/src/aqua/db.py`
- Create: `yantai-aquaculture/tests/test_db.py`

**Interfaces:**
- Produces: `db.connect(path) -> sqlite3.Connection`（自动建表）、`db.upsert_price(conn, rec)`、`db.upsert_import(conn, rec)`、`db.upsert_news(conn, rec)`、`db.price_series(conn, species) -> list[dict]`、`db.import_by_month(conn, product) -> list[dict]`、`db.news_list(conn) -> list[dict]`

- [ ] **Step 1: 写依赖与配置**

`requirements.txt`:
```
requests>=2.31
beautifulsoup4>=4.12
pytest>=8
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = src
```

- [ ] **Step 2: 安装依赖**

Run: `pip install -r requirements.txt`
Expected: 无报错（或提示已满足）

- [ ] **Step 3: 写失败测试**

`tests/test_db.py`:
```python
import sqlite3
from aqua import db


def test_connect_creates_tables():
    conn = db.connect(":memory:")
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"price", "import_stat", "news"} <= names


def test_upsert_price_and_dedup():
    conn = db.connect(":memory:")
    rec = {"species": "白虾", "date": "2026-09-01", "price": 22.5,
           "price_low": None, "price_high": None, "source": "test",
           "market": "海阳", "unit": "元/斤"}
    db.upsert_price(conn, rec)
    db.upsert_price(conn, {**rec, "price": 23.0})  # 同键应覆盖
    rows = db.price_series(conn, "白虾")
    assert len(rows) == 1
    assert rows[0]["price"] == 23.0


def test_upsert_import_and_news():
    conn = db.connect(":memory:")
    db.upsert_import(conn, {"ym": "2026-08", "product": "冻虾",
                            "volume_ton": 58000.0, "source": "test"})
    db.upsert_news(conn, {"date": "2026-09-20", "category": "病害",
                          "title": "测试新闻", "summary": "", "url": "",
                          "source": "test"})
    assert db.import_by_month(conn, "冻虾")[0]["volume_ton"] == 58000.0
    assert db.news_list(conn)[0]["title"] == "测试新闻"
```

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_db.py -v`
Expected: FAIL（ModuleNotFoundError: aqua）

- [ ] **Step 5: 实现 db.py**

`src/aqua/db.py`:
```python
"""SQLite 数据层：建表与写入。"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS price (
    id INTEGER PRIMARY KEY,
    species TEXT NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    price_low REAL,
    price_high REAL,
    source TEXT NOT NULL,
    market TEXT,
    unit TEXT NOT NULL DEFAULT '元/斤',
    UNIQUE(species, date, source, market)
);
CREATE TABLE IF NOT EXISTS import_stat (
    id INTEGER PRIMARY KEY,
    ym TEXT NOT NULL,
    product TEXT NOT NULL,
    volume_ton REAL NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(product, ym, source)
);
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    source TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_price(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """INSERT INTO price(species, date, price, price_low, price_high,
                             source, market, unit)
           VALUES(:species, :date, :price, :price_low, :price_high,
                  :source, :market, :unit)
           ON CONFLICT(species, date, source, market)
           DO UPDATE SET price=excluded.price,
                         price_low=excluded.price_low,
                         price_high=excluded.price_high,
                         unit=excluded.unit""",
        rec,
    )


def upsert_import(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """INSERT INTO import_stat(ym, product, volume_ton, source)
           VALUES(:ym, :product, :volume_ton, :source)
           ON CONFLICT(product, ym, source)
           DO UPDATE SET volume_ton=excluded.volume_ton""",
        rec,
    )


def upsert_news(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """INSERT INTO news(date, category, title, summary, url, source)
           VALUES(:date, :category, :title, :summary, :url, :source)""",
        rec,
    )


def price_series(conn: sqlite3.Connection, species: str) -> list[dict]:
    rows = conn.execute(
        "SELECT date, price, price_low, price_high, source, market "
        "FROM price WHERE species=? ORDER BY date", (species,)).fetchall()
    return [dict(r) for r in rows]


def import_by_month(conn: sqlite3.Connection, product: str) -> list[dict]:
    rows = conn.execute(
        "SELECT ym, volume_ton, source FROM import_stat "
        "WHERE product=? ORDER BY ym", (product,)).fetchall()
    return [dict(r) for r in rows]


def news_list(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT date, category, title, summary, url, source "
        "FROM news ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_db.py -v`
Expected: 3 passed

- [ ] **Step 7: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 项目骨架与SQLite数据层"
```

---

### Task 2: 数据标准化模块

**Files:**
- Create: `yantai-aquaculture/src/aqua/normalize.py`
- Create: `yantai-aquaculture/tests/test_normalize.py`

**Interfaces:**
- Consumes: 无
- Produces: `normalize.to_species(raw) -> str`、`normalize.to_iso_date(raw) -> str`、`normalize.to_yuan_per_jin(value, unit) -> float`、`normalize.normalize_record(raw) -> dict`（raw 含 `name`/`date`/`price`/`unit`/`source`/`market`，输出 upsert_price 所需字段）

- [ ] **Step 1: 写失败测试**

`tests/test_normalize.py`:
```python
import pytest
from aqua import normalize


def test_to_species_maps_aliases():
    assert normalize.to_species("南美白对虾") == "白虾"
    assert normalize.to_species("口虾蛄") == "皮皮虾"
    assert normalize.to_species("三疣梭子蟹") == "梭子蟹"
    assert normalize.to_species("牡蛎") == "生蚝"


def test_to_species_unknown_raises():
    with pytest.raises(ValueError):
        normalize.to_species("三文鱼")


def test_to_iso_date_formats():
    assert normalize.to_iso_date("2026-09-25") == "2026-09-25"
    assert normalize.to_iso_date("2026/9/5") == "2026-09-05"
    assert normalize.to_iso_date("2026-09") == "2026-09"


def test_to_yuan_per_jin():
    assert normalize.to_yuan_per_jin(44.0, "元/公斤") == 22.0
    assert normalize.to_yuan_per_jin(22.0, "元/斤") == 22.0
    assert normalize.to_yuan_per_jin(44.0, "元/kg") == 22.0


def test_normalize_record():
    raw = {"name": "南美白对虾", "date": "2026/8/15", "price": 40.0,
           "unit": "元/公斤", "source": "moa", "market": "全国均价"}
    rec = normalize.normalize_record(raw)
    assert rec["species"] == "白虾"
    assert rec["date"] == "2026-08-15"
    assert rec["price"] == 20.0
    assert rec["price_low"] is None and rec["price_high"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL（ModuleNotFoundError: aqua.normalize）

- [ ] **Step 3: 实现 normalize.py**

`src/aqua/normalize.py`:
```python
"""数据标准化：物种名、日期、价格单位统一。"""
SPECIES_MAP = {
    "南美白对虾": "白虾", "南美白虾": "白虾", "白虾": "白虾",
    "口虾蛄": "皮皮虾", "皮皮虾": "皮皮虾",
    "三疣梭子蟹": "梭子蟹", "梭子蟹": "梭子蟹",
    "牡蛎": "生蚝", "生蚝": "生蚝", "海蛎": "生蚝",
}


def to_species(raw: str) -> str:
    for key, val in SPECIES_MAP.items():
        if key in raw:
            return val
    raise ValueError(f"未知物种: {raw}")


def to_iso_date(raw: str) -> str:
    """'2026-09-25'、'2026/9/25'、'2026-09' → 'yyyy-mm-dd' / 'yyyy-mm'"""
    raw = raw.strip().replace("/", "-").replace(".", "-")
    parts = [p for p in raw.split("-") if p]
    if len(parts) == 2:
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
    if len(parts) == 3:
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    raise ValueError(f"无法解析日期: {raw}")


def to_yuan_per_jin(value: float, unit: str) -> float:
    """统一为元/斤；公斤价减半。"""
    u = unit.strip().lower()
    if "公斤" in u or "kg" in u:
        return value / 2
    return value


def normalize_record(raw: dict) -> dict:
    """数据源原始记录 → upsert_price 所需字段。"""
    return {
        "species": to_species(raw["name"]),
        "date": to_iso_date(raw["date"]),
        "price": to_yuan_per_jin(float(raw["price"]), raw.get("unit", "元/斤")),
        "price_low": raw.get("price_low"),
        "price_high": raw.get("price_high"),
        "source": raw["source"],
        "market": raw.get("market"),
        "unit": "元/斤",
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_normalize.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 数据标准化模块"
```

---

### Task 3: 农业农村部月度批发价数据源

**Files:**
- Create: `yantai-aquaculture/src/aqua/sources/__init__.py`（空文件）
- Create: `yantai-aquaculture/src/aqua/sources/base.py`
- Create: `yantai-aquaculture/src/aqua/sources/moa.py`
- Create: `yantai-aquaculture/fixtures/moa_sample.html`（执行时抓取保存）
- Create: `yantai-aquaculture/tests/test_moa.py`

**Interfaces:**
- Consumes: `normalize.normalize_record`
- Produces: `sources.moa.fetch() -> str`（下载页面）、`sources.moa.parse(text) -> list[dict]`（已 normalize 的记录，含 `species/date/price/…`）、`sources.moa.run(conn) -> int`（抓取+入库，返回入库条数）

**说明**：此任务的解析器必须按真实页面结构编写，计划无法预知 HTML 选择器。执行时先抓取样本保存 fixture 并人工检查结构，再写 parse 与测试。

- [ ] **Step 1: 写抓取辅助 base.py**

`src/aqua/sources/base.py`:
```python
"""抓取辅助：请求与 fixture 存取。"""
import pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parents[3]  # yantai-aquaculture/
FIXTURES = ROOT / "fixtures"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}


def get(url: str, timeout: int = 30) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def save_fixture(name: str, text: str) -> None:
    FIXTURES.mkdir(exist_ok=True)
    (FIXTURES / name).write_text(text, encoding="utf-8")


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")
```

- [ ] **Step 2: 抓取样本并保存 fixture**

用 Python 交互验证目标源可得性（农业农村部"重点监测水产品批发价格"页面，`http://www.moa.gov.cn` 或 `https://www.foods1.com` 等行情转载页均可接受，以真实可得为准）：

```bash
python -c "from aqua.sources import base; base.save_fixture('moa_sample.html', base.get('<验证后的URL>'))"
```

Expected: fixtures/moa_sample.html 存在且含价格字样。**若官方站反爬/不可得：记录缺口，改试 foods1.com、中国水产信息网等转载源；全部失败则本任务降级为"人工月度录入"（同 Task 5 的 import_manual 模式），并在此步骤的 commit message 中说明。**

- [ ] **Step 3: 检查 fixture 结构，写失败测试**

打开 `fixtures/moa_sample.html`，定位品种名称、日期、价格所在的表格/标签结构，然后写测试（示例，按实际结构调整选择器）：

`tests/test_moa.py`:
```python
from aqua.sources import base, moa


def test_parse_moa_fixture():
    text = base.load_fixture("moa_sample.html")
    records = moa.parse(text)
    assert len(records) >= 3
    species = {r["species"] for r in records}
    assert "白虾" in species
    for r in records:
        assert r["date"] and r["price"] > 0
        assert r["unit"] == "元/斤"
        assert r["source"] == "moa"
```

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_moa.py -v`
Expected: FAIL（parse 未实现）

- [ ] **Step 5: 实现 moa.py（按 fixture 实际结构写 parse）**

```python
"""农业农村部月度批发价数据源。"""
from bs4 import BeautifulSoup
from .. import normalize
from . import base

URL = ""  # Step 2 验证后填入


def fetch() -> str:
    return base.get(URL)


def parse(text: str) -> list[dict]:
    """解析页面 → 标准化记录列表。选择器按 fixture 实际结构实现。"""
    soup = BeautifulSoup(text, "html.parser")
    records = []
    # 在此按 fixture 结构逐行解析：
    # for row in soup.select("<实际选择器>"):
    #     raw = {"name": ..., "date": ..., "price": ..., "unit": ..., ...}
    #     records.append(normalize.normalize_record({**raw, "source": "moa"}))
    return records


def run(conn) -> int:
    from .. import db
    n = 0
    for rec in parse(fetch()):
        db.upsert_price(conn, rec)
        n += 1
    conn.commit()
    return n
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_moa.py -v`
Expected: PASS

- [ ] **Step 7: 真实抓取入库验证**

```bash
python -c "from aqua import db; from aqua.sources import moa; conn = db.connect('yantai-aquaculture/data/aquarium.db'); print('入库', moa.run(conn), '条')"
```

Expected: 打印入库条数 > 0；`data/aquarium.db` 出现

- [ ] **Step 8: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 农业农村部数据源"
```

---

### Task 4: 月度虾类进口量数据源

**Files:**
- Create: `yantai-aquaculture/src/aqua/sources/customs.py`
- Create: `yantai-aquaculture/tests/test_customs.py`
- Create: `yantai-aquaculture/data/import_manual.json`（若走人工模式）

**Interfaces:**
- Consumes: `db.upsert_import`
- Produces: `sources.customs.run(conn) -> int`（返回入库条数）

**说明**：海关官方统计查询平台需交互式查询，直接爬取成功率低。**优先方案：人工月度录入**——每月由维护者把"冻虾/虾类进口量（吨）"写进 `data/import_manual.json`，`run()` 读取入库。若执行时发现可爬的行业转载源（如中国水产频道月度文章），再加 parse；否则维持人工模式。

- [ ] **Step 1: 写失败测试**

`tests/test_customs.py`:
```python
import json
from aqua import db
from aqua.sources import customs


def test_run_imports_manual_file(tmp_path):
    manual = tmp_path / "import_manual.json"
    manual.write_text(json.dumps([
        {"ym": "2026-07", "product": "冻虾", "volume_ton": 61000,
         "source": "海关月度"},
        {"ym": "2026-08", "product": "冻虾", "volume_ton": 58000,
         "source": "海关月度"},
    ], ensure_ascii=False), encoding="utf-8")
    conn = db.connect(":memory:")
    n = customs.run(conn, path=str(manual))
    assert n == 2
    assert db.import_by_month(conn, "冻虾")[0]["volume_ton"] == 61000
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_customs.py -v`
Expected: FAIL（customs 未实现）

- [ ] **Step 3: 实现 customs.py**

```python
"""月度虾类进口量：人工录入 JSON → 入库。"""
import json
import pathlib
from .. import db

DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "import_manual.json"


def run(conn, path=None) -> int:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    if not p.exists():
        print(f"[customs] 未找到 {p}，跳过（首次运行先建立该文件）")
        return 0
    data = json.loads(p.read_text(encoding="utf-8"))
    for rec in data:
        db.upsert_import(conn, rec)
    conn.commit()
    return len(data)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_customs.py -v`
Expected: PASS

- [ ] **Step 5: 建立初始 import_manual.json**

用 WebSearch 查最近 3 个月"中国冻虾进口量"数据，填入：

`data/import_manual.json`（示例结构）:
```json
[
  {"ym": "2026-06", "product": "冻虾", "volume_ton": 0, "source": "海关月度"},
  {"ym": "2026-07", "product": "冻虾", "volume_ton": 0, "source": "海关月度"},
  {"ym": "2026-08", "product": "冻虾", "volume_ton": 0, "source": "海关月度"}
]
```

（volume_ton 填入查到的真实值；查不到就删除对应行，宁缺毋假）

- [ ] **Step 6: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 进口量人工录入数据源"
```

---

### Task 5: 惠农网周度报价数据源（含皮皮虾）

**Files:**
- Create: `yantai-aquaculture/src/aqua/sources/huinong.py`
- Create: `yantai-aquaculture/fixtures/huinong_sample.html`（执行时抓取）
- Create: `yantai-aquaculture/tests/test_huinong.py`

**Interfaces:**
- Produces: `sources.huinong.parse(text) -> list[dict]`、`sources.huinong.run(conn) -> int`

**说明**：惠农网为商业站，可能反爬；皮皮虾报价可能稀疏。执行顺序：先验证页面可得性 → 无则换同类源（中国水产信息网、食品商务网行情页）→ 再不行本任务降级为"周度人工录入"（结构与 import_manual 相同）。**本任务允许失败降级，不影响整体。**

- [ ] **Step 1: 抓样本存 fixture**

```bash
python -c "from aqua.sources import base; base.save_fixture('huinong_sample.html', base.get('<验证后的URL>'))"
```

Expected: fixture 含报价数据；若失败按上述说明降级（降级时本任务后续步骤改为实现"周度人工录入 JSON 源"，结构与 Task 4 相同，测试同构）。

- [ ] **Step 2: 检查 fixture，写失败测试**

`tests/test_huinong.py`:
```python
from aqua.sources import base, huinong


def test_parse_huinong_fixture():
    text = base.load_fixture("huinong_sample.html")
    records = huinong.parse(text)
    assert len(records) >= 2
    for r in records:
        assert r["date"] and r["price"] > 0
        assert r["unit"] == "元/斤"
        assert r["source"] == "huinong"
```

- [ ] **Step 3: 运行测试确认失败 → 按 fixture 结构实现 huinong.py → 运行测试确认通过**

结构与 Task 3 相同（fetch/parse/run 三函数），parse 按 fixture 实际结构编写。

- [ ] **Step 4: 真实抓取入库验证 + 提交**

```bash
python -c "from aqua import db; from aqua.sources import huinong; conn = db.connect('yantai-aquaculture/data/aquarium.db'); print('入库', huinong.run(conn), '条')"
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 惠农网数据源"
```

---

### Task 6: 全流程管道 + CSV 备份

**Files:**
- Create: `yantai-aquaculture/src/aqua/pipeline.py`
- Create: `yantai-aquaculture/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `sources.moa.run`、`sources.customs.run`、`sources.huinong.run`、`db.connect`
- Produces: `pipeline.run(db_path) -> dict`（返回各源入库条数统计）、`pipeline.backup_csv(conn, csv_dir) -> None`

- [ ] **Step 1: 写失败测试**

`tests/test_pipeline.py`:
```python
from aqua import db, pipeline


def test_run_skips_failed_source_and_backs_up(tmp_path, monkeypatch):
    def boom(conn):
        raise RuntimeError("源挂了")
    monkeypatch.setattr("aqua.sources.moa.run", boom)

    def ok(conn):
        db.upsert_price(conn, {"species": "白虾", "date": "2026-09-01",
                               "price": 22.0, "price_low": None,
                               "price_high": None, "source": "test",
                               "market": "海阳", "unit": "元/斤"})
        conn.commit()
        return 1
    monkeypatch.setattr("aqua.sources.huinong.run", ok)
    monkeypatch.setattr("aqua.sources.customs.run", lambda conn, path=None: 0)

    db_path = str(tmp_path / "test.db")
    result = pipeline.run(db_path, csv_dir=str(tmp_path))
    assert result["moa"] == 0        # 失败源记 0，不抛异常
    assert result["huinong"] == 1
    csvs = list(tmp_path.glob("*.csv"))
    assert len(csvs) >= 1            # 备份已生成
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL（pipeline 未实现）

- [ ] **Step 3: 实现 pipeline.py**

```python
"""全流程入口：各源抓取 → 入库 → CSV 备份。"""
import csv
import pathlib
from . import db
from .sources import moa, customs, huinong


def run(db_path: str, csv_dir: str = None) -> dict:
    conn = db.connect(db_path)
    stats = {}
    for name, fn in [("moa", moa.run), ("customs", customs.run),
                     ("huinong", huinong.run)]:
        try:
            stats[name] = fn(conn)
            print(f"[pipeline] {name}: {stats[name]} 条")
        except Exception as e:  # 单源失败不拖垮整体
            print(f"[pipeline] {name} 失败，跳过: {e}")
            stats[name] = 0
    if csv_dir:
        backup_csv(conn, csv_dir)
    return stats


def backup_csv(conn, csv_dir: str) -> None:
    out = pathlib.Path(csv_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        "SELECT species, date, price, price_low, price_high, source, market "
        "FROM price ORDER BY species, date").fetchall()
    with (out / "price.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["species", "date", "price", "price_low", "price_high",
                    "source", "market"])
        w.writerows([tuple(r) for r in rows])
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: 全量真实运行**

```bash
python -c "from aqua import pipeline; print(pipeline.run('yantai-aquaculture/data/aquarium.db', csv_dir='yantai-aquaculture/data'))"
```

Expected: 各源条数打印，无崩溃；`data/price.csv` 生成

- [ ] **Step 6: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 全流程管道与CSV备份"
```

**M1 验收：** 三源（或降级替代）数据落库可重复跑、单源失败不影响整体、CSV 备份生成。

---

## 里程碑 M2：走势图看板（T7-T8）

### Task 7: 配置模块 + 站点构建器 + 首页看板

**Files:**
- Create: `yantai-aquaculture/src/aqua/config.py`
- Create: `yantai-aquaculture/src/aqua/web/__init__.py`（空文件）
- Create: `yantai-aquaculture/src/aqua/web/build.py`
- Create: `yantai-aquaculture/src/aqua/web/templates/index.html`
- Create: `yantai-aquaculture/tests/test_build.py`

**Interfaces:**
- Consumes: `db.price_series`、`db.import_by_month`
- Produces: `config.HOLIDAYS`、`config.SCENARIOS`、`build.build(db_path, out_dir) -> None`（生成 site/index.html）

- [ ] **Step 1: 写 config.py（节假日 + 情景修正）**

`src/aqua/config.py`:
```python
"""全局配置：节假日标注、预测情景修正系数、成本默认值。"""

# 春节/中秋日期（2020-2028）。执行时用搜索核实 2027、2028 年中秋，
# 有误就地修正；月报与看板共用此表。
HOLIDAYS = [
    {"name": "春节", "date": "2020-01-25"},
    {"name": "春节", "date": "2021-02-12"},
    {"name": "春节", "date": "2022-02-01"},
    {"name": "春节", "date": "2023-01-22"},
    {"name": "春节", "date": "2024-02-10"},
    {"name": "春节", "date": "2025-01-29"},
    {"name": "春节", "date": "2026-02-17"},
    {"name": "中秋", "date": "2020-10-01"},
    {"name": "中秋", "date": "2021-09-21"},
    {"name": "中秋", "date": "2022-09-10"},
    {"name": "中秋", "date": "2023-09-29"},
    {"name": "中秋", "date": "2024-09-17"},
    {"name": "中秋", "date": "2025-10-06"},
    {"name": "中秋", "date": "2026-09-25"},
]

# 预测情景修正系数（初始默认值，随数据积累校准）
SCENARIOS = [
    {"key": "normal", "label": "正常年份", "factor": 1.0},
    {"key": "import_up", "label": "进口大增", "factor": 0.95},
    {"key": "import_down", "label": "进口收缩", "factor": 1.05},
    {"key": "disease", "label": "病害减产", "factor": 1.10},
]

# 成本计算器默认值（Task 13 使用）
COST_DEFAULTS = {
    "miao_wan": 30,          # 投苗量（万尾）
    "miao_price": 120,       # 苗价（元/万尾）
    "feed_price": 4.5,       # 饲料单价（元/斤）
    "feed_ratio": 1.2,       # 饲料系数（斤饲料/斤虾）
    "elec": 3000,            # 电费（元）
    "med": 2000,             # 药费（元）
    "other": 5000,           # 其他（元）
    "survival": 0.7,         # 成活率
    "size_jin": 0.055,       # 规格（斤/尾，约18头/斤）
}
```

- [ ] **Step 2: 写失败测试**

`tests/test_build.py`:
```python
from aqua import db
from aqua.web import build


def test_build_generates_index_with_data(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.upsert_price(conn, {"species": "白虾", "date": "2026-08-15",
                           "price": 22.0, "price_low": None,
                           "price_high": None, "source": "test",
                           "market": "海阳", "unit": "元/斤"})
    conn.commit()
    out = tmp_path / "site"
    build.build(str(tmp_path / "t.db"), str(out))
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "白虾" in html
    assert "echarts.min.js" in html
    assert '"price": 22.0' in html
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_build.py -v`
Expected: FAIL（build 未实现）

- [ ] **Step 4: 实现 build.py**

`src/aqua/web/build.py`:
```python
"""静态站点生成：SQLite → site/。模板用 __XXX__ 占位符替换，无模板引擎。"""
import json
import pathlib
import shutil
import urllib.request
from .. import config, db

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
ECHARTS_URL = ("https://registry.npmmirror.com/echarts/5.5.0/"
               "files/dist/echarts.min.js")

SPECIES = ["白虾", "皮皮虾", "梭子蟹", "生蚝"]


def _vendor_echarts(out: pathlib.Path) -> None:
    """下载 echarts.min.js 到 site/assets（本地优先，不依赖 CDN）。"""
    target = out / "assets" / "echarts.min.js"
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ECHARTS_URL, timeout=60) as r:
        target.write_bytes(r.read())
    print(f"[build] echarts 已下载: {target}")


def build(db_path: str, out_dir: str) -> None:
    conn = db.connect(db_path)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _vendor_echarts(out)

    series = {s: db.price_series(conn, s) for s in SPECIES}
    imports = db.import_by_month(conn, "冻虾")

    (out / "index.html").write_text(
        (TEMPLATES / "index.html").read_text(encoding="utf-8")
        .replace("__PRICE_SERIES__", json.dumps(series, ensure_ascii=False))
        .replace("__IMPORTS__", json.dumps(imports, ensure_ascii=False))
        .replace("__HOLIDAYS__", json.dumps(config.HOLIDAYS, ensure_ascii=False)),
        encoding="utf-8",
    )
    print(f"[build] site 已生成: {out}")
```

- [ ] **Step 5: 实现 index.html 模板**

`src/aqua/web/templates/index.html`（要点：手机优先 viewport；顶部品种切换 tab；ECharts 折线图展示所选品种全历史价格；节假日用 markLine 标注；底部进口量柱状图；页面底部署数据口径说明）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>烟台海产行情</title>
<style>
  body { margin: 0; font-family: system-ui, "Microsoft YaHei", sans-serif;
         background: #f5f6f8; }
  header { background: #14532d; color: #fff; padding: 12px 16px;
           font-size: 18px; font-weight: 600; }
  .tabs { display: flex; gap: 8px; padding: 10px 12px; flex-wrap: wrap; }
  .tab { padding: 8px 14px; border-radius: 16px; background: #fff;
         font-size: 15px; border: 1px solid #ddd; }
  .tab.active { background: #14532d; color: #fff; border-color: #14532d; }
  #chart, #import-chart { width: 100%; height: 340px; background: #fff; }
  .card { background: #fff; margin: 10px 12px; border-radius: 10px;
          padding: 12px; }
  .note { font-size: 12px; color: #888; margin: 8px 12px 20px; }
  a { color: #14532d; text-decoration: none; }
  nav { display: flex; justify-content: space-around; background: #fff;
        padding: 10px 0; border-top: 1px solid #eee; font-size: 14px;
        position: sticky; bottom: 0; }
</style>
</head>
<body>
<header>烟台海产行情</header>
<div class="tabs" id="tabs"></div>
<div class="card"><div id="chart"></div></div>
<div class="card"><h3 style="margin:4px 0 8px;font-size:15px">冻虾月度进口量（吨）</h3>
  <div id="import-chart"></div></div>
<nav>
  <a href="index.html">行情</a><a href="forecast.html">预测</a>
  <a href="news.html">新闻</a><a href="cost.html">成本</a>
  <a href="guide.html">新手</a>
</nav>
<div class="note">数据口径：全国主要批发市场公开报价，与海阳当地成交价存在价差，仅供参考，不构成买卖建议。数据源：农业农村部/海关/惠农网。</div>
<script src="assets/echarts.min.js"></script>
<script>
const SERIES = __PRICE_SERIES__;
const IMPORTS = __IMPORTS__;
const HOLIDAYS = __HOLIDAYS__;
const SPECIES = ["白虾", "皮皮虾", "梭子蟹", "生蚝"];

const tabs = document.getElementById("tabs");
const chart = echarts.init(document.getElementById("chart"));
const importChart = echarts.init(document.getElementById("import-chart"));
let current = "白虾";

function renderTabs() {
  tabs.innerHTML = "";
  SPECIES.forEach(s => {
    const el = document.createElement("div");
    el.className = "tab" + (s === current ? " active" : "");
    el.textContent = s;
    el.onclick = () => { current = s; renderTabs(); renderChart(); };
    tabs.appendChild(el);
  });
}

function renderChart() {
  const rows = SERIES[current] || [];
  const markLines = HOLIDAYS.map(h => ({
    xAxis: h.date,
    lineStyle: { color: "#e11d48", type: "dashed" },
    label: { formatter: h.name, fontSize: 11 },
  }));
  chart.setOption({
    grid: { left: 44, right: 12, top: 24, bottom: 28 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "time" },
    yAxis: { type: "value", name: "元/斤", scale: true },
    series: [{
      type: "line", data: rows.map(r => [r.date, r.price]),
      symbol: "circle", symbolSize: 4, lineStyle: { width: 2 },
      markLine: { symbol: "none", data: markLines, silent: true },
    }],
  });
}

renderTabs(); renderChart();
importChart.setOption({
  grid: { left: 60, right: 12, top: 16, bottom: 28 },
  xAxis: { type: "category", data: IMPORTS.map(r => r.ym) },
  yAxis: { type: "value" },
  series: [{ type: "bar", data: IMPORTS.map(r => r.volume_ton),
             itemStyle: { color: "#0f766e" } }],
});
</script>
</body>
</html>
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_build.py -v`
Expected: PASS（首次运行会下载 echarts，较慢）

- [ ] **Step 7: 真实构建 + 浏览器验收**

```bash
python -c "from aqua.web import build; build.build('yantai-aquaculture/data/aquarium.db', 'yantai-aquaculture/site')"
```

Expected: site/index.html 生成，`start site/index.html` 浏览器打开可见曲线与进口柱状图，手机窗口宽度（约 380px）布局正常。

- [ ] **Step 8: .gitignore 补充 + 提交**

在 `E:\ClaudeCode\.gitignore` 末尾追加两行：`yantai-aquaculture/site/`、`yantai-aquaculture/data/aquarium.db`

```bash
git -C /e/ClaudeCode add yantai-aquaculture .gitignore
git -C /e/ClaudeCode commit -m "新增: 行情看板首页"
```

---

### Task 8: 本地验收 M2

- [ ] **Step 1: 手机同网访问验证**

在开发电脑上 `python -m http.server 8000 --directory yantai-aquaculture/site`，手机连同一 WiFi 打开 `http://<电脑IP>:8000`。Expected: 手机可看、可切品种、图表正常。

- [ ] **Step 2: 把验收结果记入 docs/联调验收清单.md（新增文件，仿酒店项目格式），提交**

**M2 验收标准：** 本地打开可见历史曲线；手机布局正常；春节/中秋标注出现。

---

## 里程碑 M3：预测器（T9-T10）

### Task 9: 出虾窗口价格统计（预测器核心计算）

**Files:**
- Create: `yantai-aquaculture/src/aqua/forecast.py`
- Create: `yantai-aquaculture/tests/test_forecast.py`

**Interfaces:**
- Consumes: `db.price_series`
- Produces: `forecast.window_stats(conn, species, start_md, end_md, years=5) -> dict`，返回 `{count, median, p25, p75, min, max, by_year: {yyyy: {count, avg}}}`；`start_md`/`end_md` 形如 `"08-15"`，支持跨年窗口（start > end 时视为跨年，如 `"12-20"` ~ `"02-10"`）

- [ ] **Step 1: 写失败测试**

`tests/test_forecast.py`:
```python
from aqua import db, forecast


def _seed(conn):
    # 2022-2026 每年 8-9 月白虾价格，逐年递增便于断言
    for i, year in enumerate(range(2022, 2027)):
        for day in ("08-15", "09-01", "09-15"):
            db.upsert_price(conn, {"species": "白虾",
                                   "date": f"{year}-{day}",
                                   "price": 20.0 + i, "price_low": None,
                                   "price_high": None, "source": "test",
                                   "market": "海阳", "unit": "元/斤"})
    conn.commit()


def test_window_stats_basic():
    conn = db.connect(":memory:")
    _seed(conn)
    s = forecast.window_stats(conn, "白虾", "08-10", "09-20")
    assert s["count"] == 15
    assert s["median"] == 22.0
    assert s["min"] == 20.0 and s["max"] == 24.0
    assert s["by_year"]["2022"]["count"] == 3
    assert s["by_year"]["2022"]["avg"] == 20.0


def test_window_stats_cross_year():
    conn = db.connect(":memory:")
    for year in (2022, 2023):
        db.upsert_price(conn, {"species": "皮皮虾",
                               "date": f"{year}-12-25", "price": 45.0,
                               "price_low": None, "price_high": None,
                               "source": "test", "market": "海阳",
                               "unit": "元/斤"})
        db.upsert_price(conn, {"species": "皮皮虾",
                               "date": f"{year}-01-10", "price": 50.0,
                               "price_low": None, "price_high": None,
                               "source": "test", "market": "海阳",
                               "unit": "元/斤"})
    conn.commit()
    s = forecast.window_stats(conn, "皮皮虾", "12-20", "01-15")
    assert s["count"] == 4
    # 2022-12 的跨年记录应归入"出虾年" 2023
    assert s["by_year"]["2023"]["count"] == 2


def test_window_stats_empty():
    conn = db.connect(":memory:")
    s = forecast.window_stats(conn, "白虾", "08-10", "09-20")
    assert s["count"] == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_forecast.py -v`
Expected: FAIL（forecast 未实现）

- [ ] **Step 3: 实现 forecast.py**

```python
"""出虾窗口价格统计：预测器核心。给区间不给点。"""
from statistics import quantiles
from . import db


def _in_window(md: str, start: str, end: str) -> bool:
    """md='mm-dd'；start>end 视为跨年窗口。"""
    if start <= end:
        return start <= md <= end
    return md >= start or md <= end


def window_stats(conn, species: str, start_md: str, end_md: str,
                 years: int = 5) -> dict:
    """近 years 年内落在 [start_md, end_md] 窗口的价格统计。"""
    rows = db.price_series(conn, species)
    sel = [r for r in rows if _in_window(r["date"][5:10], start_md, end_md)]
    if not sel:
        return {"count": 0}
    prices = sorted(r["price"] for r in sel)
    q = quantiles(prices, n=4)  # [p25, p50, p75]
    by_year: dict[str, list] = {}
    cross = start_md > end_md
    for r in sel:
        y = int(r["date"][:4])
        # 跨年窗口：12 月记录归入次年（出虾年）
        if cross and r["date"][5:10] >= start_md:
            y += 1
        by_year.setdefault(str(y), []).append(r["price"])
    return {
        "count": len(sel),
        "median": round(q[1], 2),
        "p25": round(q[0], 2),
        "p75": round(q[2], 2),
        "min": min(prices),
        "max": max(prices),
        "by_year": {y: {"count": len(v),
                        "avg": round(sum(v) / len(v), 2)}
                    for y, v in sorted(by_year.items())},
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_forecast.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 出虾窗口价格统计"
```

---

### Task 10: 预测器页面

**Files:**
- Modify: `yantai-aquaculture/src/aqua/web/build.py`（生成 forecast.html）
- Create: `yantai-aquaculture/src/aqua/web/templates/forecast.html`
- Modify: `yantai-aquaculture/tests/test_build.py`（补 forecast 断言）

**Interfaces:**
- Consumes: `config.SCENARIOS`、`db.price_series`

- [ ] **Step 1: 补失败测试**

`tests/test_build.py` 追加:
```python
def test_build_generates_forecast(tmp_path):
    conn = db.connect(str(tmp_path / "t2.db"))
    conn.commit()
    out = tmp_path / "site2"
    build.build(str(tmp_path / "t2.db"), str(out))
    html = (out / "forecast.html").read_text(encoding="utf-8")
    assert "历史统计" in html
    assert "不构成预测保证" in html
```

- [ ] **Step 2: 运行测试确认失败（build 未生成 forecast.html）**

- [ ] **Step 3: build.py 增加 forecast 生成**

`build()` 内追加：
```python
    (out / "forecast.html").write_text(
        (TEMPLATES / "forecast.html").read_text(encoding="utf-8")
        .replace("__PRICE_SERIES__", json.dumps(series, ensure_ascii=False))
        .replace("__SCENARIOS__", json.dumps(config.SCENARIOS, ensure_ascii=False)),
        encoding="utf-8",
    )
```

- [ ] **Step 4: 实现 forecast.html 模板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>出虾价格区间</title>
<style>
  body { margin: 0; font-family: system-ui, "Microsoft YaHei", sans-serif;
         background: #f5f6f8; }
  header { background: #14532d; color: #fff; padding: 12px 16px;
           font-size: 18px; font-weight: 600; }
  .card { background: #fff; margin: 10px 12px; border-radius: 10px;
          padding: 14px; }
  label { font-size: 14px; color: #333; display: block; margin: 10px 0 4px; }
  select, input { width: 100%; font-size: 16px; padding: 8px;
                  border: 1px solid #ccc; border-radius: 6px;
                  box-sizing: border-box; }
  button { width: 100%; margin-top: 16px; padding: 12px; font-size: 16px;
           background: #14532d; color: #fff; border: 0; border-radius: 8px; }
  #result { margin-top: 14px; font-size: 15px; line-height: 1.8; }
  .big { font-size: 22px; font-weight: 700; color: #14532d; }
  .warn { font-size: 12px; color: #999; margin-top: 10px; }
  nav { display: flex; justify-content: space-around; background: #fff;
        padding: 10px 0; border-top: 1px solid #eee; font-size: 14px;
        position: sticky; bottom: 0; }
  a { color: #14532d; text-decoration: none; }
</style>
</head>
<body>
<header>出虾价格区间</header>
<div class="card">
  <label>品种</label>
  <select id="species">
    <option>白虾</option><option>皮皮虾</option>
    <option>梭子蟹</option><option>生蚝</option>
  </select>
  <label>投苗日期（参考用）</label>
  <input type="date" id="stock">
  <label>预计出虾：从</label>
  <input type="date" id="from">
  <label>到</label>
  <input type="date" id="to">
  <label>今年情景</label>
  <select id="scenario"></select>
  <button onclick="calc()">查历史价格区间</button>
  <div id="result"></div>
  <div class="warn">本结果基于历史价格统计，不构成预测保证；实际成交受病害、天气、进口等影响，仅供参考。</div>
</div>
<nav>
  <a href="index.html">行情</a><a href="forecast.html">预测</a>
  <a href="news.html">新闻</a><a href="cost.html">成本</a>
  <a href="guide.html">新手</a>
</nav>
<script>
const SERIES = __PRICE_SERIES__;
const SCENARIOS = __SCENARIOS__;

const sel = document.getElementById("scenario");
SCENARIOS.forEach(s => {
  const o = document.createElement("option");
  o.value = s.factor; o.textContent = s.label;
  sel.appendChild(o);
});

function md(d) { return d.slice(5, 10); }
function inWindow(x, a, b) { return a <= b ? (a <= x && x <= b)
                                           : (x >= a || x <= b); }

function calc() {
  const sp = document.getElementById("species").value;
  const a = md(document.getElementById("from").value);
  const b = md(document.getElementById("to").value);
  if (!a || !b) { document.getElementById("result").innerHTML =
      "请填出虾起止日期"; return; }
  const rows = (SERIES[sp] || []).filter(r => inWindow(md(r.date), a, b));
  const factor = parseFloat(sel.value);
  const el = document.getElementById("result");
  if (!rows.length) { el.innerHTML = "该窗口暂无历史数据"; return; }
  const prices = rows.map(r => r.price).sort((x, y) => x - y);
  const q = p => prices[Math.min(prices.length - 1,
                                 Math.floor(prices.length * p))];
  const mid = q(0.5), lo = q(0.25), hi = q(0.75);
  const byYear = {};
  rows.forEach(r => { const y = r.date.slice(0, 4);
    (byYear[y] = byYear[y] || []).push(r.price); });
  const rowsHtml = Object.keys(byYear).sort().map(y => {
    const avg = byYear[y].reduce((s, v) => s + v, 0) / byYear[y].length;
    return `<tr><td>${y}</td><td>${byYear[y].length}条</td>
            <td>${avg.toFixed(1)}</td></tr>`; }).join("");
  el.innerHTML =
    `<div>该窗口近5年共 <b>${rows.length}</b> 条价格记录</div>
     <div class="big">中位价 ${mid.toFixed(1)} 元/斤</div>
     <div>常规区间 ${lo.toFixed(1)} ~ ${hi.toFixed(1)} 元/斤
          （历史最低 ${Math.min(...prices).toFixed(1)} /
           最高 ${Math.max(...prices).toFixed(1)}）</div>
     <div style="margin-top:8px">${sel.selectedOptions[0].textContent}修正后：
        <b>${(lo * factor).toFixed(1)} ~ ${(hi * factor).toFixed(1)} 元/斤</b></div>
     <table style="width:100%;margin-top:10px;border-collapse:collapse">
       <tr><th style="text-align:left">年份</th>
           <th style="text-align:left">记录</th>
           <th style="text-align:left">窗口均价</th></tr>${rowsHtml}</table>`;
}
</script>
</body>
</html>
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_build.py -v`
Expected: 2 passed

- [ ] **Step 6: 构建并手动验证预测器交互**

```bash
python -c "from aqua.web import build; build.build('yantai-aquaculture/data/aquarium.db', 'yantai-aquaculture/site')"
```

浏览器打开 site/forecast.html：选白虾、from=08-15、to=09-15，Expected: 显示中位价、区间、分年表；跨年窗口（12-20 ~ 02-10）正常。

- [ ] **Step 7: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 出虾价格区间预测器页面"
```

**M3 验收：** 输入投苗/出虾时间返回历史区间与分年对比；跨年窗口正确；免责说明可见。

---

## 里程碑 M4：新闻雷达（T11-T12）

### Task 11: 人工新闻录入 + 新闻页

**Files:**
- Create: `yantai-aquaculture/src/aqua/newsman.py`
- Create: `yantai-aquaculture/src/aqua/web/templates/news.html`
- Create: `yantai-aquaculture/tests/test_newsman.py`
- Modify: `yantai-aquaculture/src/aqua/web/build.py`（生成 news.html）
- Modify: `yantai-aquaculture/tests/test_build.py`（补 news 断言）

**Interfaces:**
- Consumes: `db.upsert_news`、`db.news_list`
- Produces: `newsman.run(conn, path=None) -> int`（读 data/news_manual.json 入库，按 (date,title) 去重）

**说明**：M4 按"先人工周选两个月验证，再决定自动化"。人工模式 = 维护者每周用 WebSearch 汇总病害/进口/政策/天气新闻，写入 `data/news_manual.json`，运行管道入库，页面展示。

- [ ] **Step 1: 写失败测试**

`tests/test_newsman.py`:
```python
import json
from aqua import db, newsman


def test_run_imports_and_dedups(tmp_path):
    f = tmp_path / "news_manual.json"
    f.write_text(json.dumps([
        {"date": "2026-09-20", "category": "病害", "title": "某地白斑病",
         "summary": "内容摘要", "url": "https://example.com/1",
         "source": "人工周选"},
    ], ensure_ascii=False), encoding="utf-8")
    conn = db.connect(":memory:")
    assert newsman.run(conn, path=str(f)) == 1
    assert newsman.run(conn, path=str(f)) == 0  # 重复运行不再入库
    assert db.news_list(conn)[0]["category"] == "病害"
```

- [ ] **Step 2: 运行测试确认失败 → 实现 newsman.py → 运行测试确认通过**

`src/aqua/newsman.py`:
```python
"""人工新闻周选：data/news_manual.json → 入库（按日期+标题去重）。"""
import json
import pathlib
from . import db

DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "news_manual.json"


def run(conn, path=None) -> int:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    if not p.exists():
        print(f"[newsman] 未找到 {p}，跳过")
        return 0
    items = json.loads(p.read_text(encoding="utf-8"))
    existing = {(r["date"], r["title"]) for r in db.news_list(conn)}
    n = 0
    for rec in items:
        if (rec["date"], rec["title"]) in existing:
            continue
        db.upsert_news(conn, rec)
        n += 1
    conn.commit()
    return n
```

- [ ] **Step 3: build.py 生成 news.html + 实现模板**

build() 追加：
```python
    news = db.news_list(conn)
    (out / "news.html").write_text(
        (TEMPLATES / "news.html").read_text(encoding="utf-8")
        .replace("__NEWS__", json.dumps(news, ensure_ascii=False)),
        encoding="utf-8",
    )
```

`templates/news.html`（与 index 同 header/nav 样式；按日期倒序渲染列表；分类用彩色标签：病害=红、进口=蓝、政策=绿、天气=橙；每条含标题（可点开 url）、摘要、来源与日期）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>行业新闻</title>
<style>
  body { margin: 0; font-family: system-ui, "Microsoft YaHei", sans-serif;
         background: #f5f6f8; }
  header { background: #14532d; color: #fff; padding: 12px 16px;
           font-size: 18px; font-weight: 600; }
  .item { background: #fff; margin: 10px 12px; border-radius: 10px;
          padding: 12px; }
  .title { font-size: 15px; font-weight: 600; color: #111; }
  .summary { font-size: 13px; color: #555; margin-top: 6px; }
  .meta { font-size: 12px; color: #999; margin-top: 6px; }
  .tag { display: inline-block; font-size: 11px; padding: 2px 8px;
         border-radius: 8px; color: #fff; margin-right: 6px; }
  nav { display: flex; justify-content: space-around; background: #fff;
        padding: 10px 0; border-top: 1px solid #eee; font-size: 14px;
        position: sticky; bottom: 0; }
  a { color: #14532d; text-decoration: none; }
</style>
</head>
<body>
<header>行业新闻</header>
<div id="list"></div>
<nav>
  <a href="index.html">行情</a><a href="forecast.html">预测</a>
  <a href="news.html">新闻</a><a href="cost.html">成本</a>
  <a href="guide.html">新手</a>
</nav>
<script>
const NEWS = __NEWS__;
const COLORS = { "病害": "#dc2626", "进口": "#2563eb",
                 "政策": "#16a34a", "天气": "#ea580c" };
const list = document.getElementById("list");
NEWS.forEach(n => {
  const el = document.createElement("div");
  el.className = "item";
  const color = COLORS[n.category] || "#666";
  const title = n.url
    ? `<a class="title" href="${n.url}" target="_blank">${n.title}</a>`
    : `<span class="title">${n.title}</span>`;
  el.innerHTML = `<span class="tag" style="background:${color}">${n.category}</span>
    ${title}
    <div class="summary">${n.summary || ""}</div>
    <div class="meta">${n.date} · ${n.source}</div>`;
  list.appendChild(el);
});
</script>
</body>
</html>
```

- [ ] **Step 4: 补 build 测试断言并跑绿**

`test_build_generates_news`: 构建含一条新闻的库，断言 news.html 含标题文字。

- [ ] **Step 5: 首次新闻采集入库**

用 WebSearch 汇总本周（2026-09-19 ~ 09-25）病害/进口/政策/天气四类各 2-4 条真实新闻，写 `data/news_manual.json`，运行：
```bash
python -c "from aqua import db; from aqua import newsman; conn = db.connect('yantai-aquaculture/data/aquarium.db'); print(newsman.run(conn), '条')"
```

- [ ] **Step 6: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 新闻周选导入与新闻页"
```

---

### Task 12: 新闻管道接入 + 周选流程文档

- [ ] **Step 1: pipeline.py 接入 newsman.run**

pipeline.run 的循环列表改为 `[("moa", moa.run), ("customs", customs.run), ("huinong", huinong.run), ("news", newsman.run)]`（newsman 同样 try/except 保护），并更新 test_pipeline 的 monkeypatch（补 `newsman.run`）。

- [ ] **Step 2: 写周选操作说明**

新增 `yantai-aquaculture/docs/维护手册.md`：数据更新命令（pipeline + build 两条 python 命令）、新闻周选格式样例、进口量月度录入格式、常见故障（某源失败=跳过可查打印）。

- [ ] **Step 3: 全量测试 + 提交**

Run: `pytest`（全部测试绿）
```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 新闻管道接入与维护手册"
```

**M4 验收：** 新闻可人工录入并出现在手机页；维护手册写清更新流程。自动化爬虫与否等朋友实际使用两个月后再定。

---

## 里程碑 M5：成本计算器 + 新手内容 + 月报（T13-T16）

### Task 13: 成本模型与保本价计算器

**Files:**
- Create: `yantai-aquaculture/src/aqua/costcalc.py`
- Create: `yantai-aquaculture/tests/test_costcalc.py`
- Create: `yantai-aquaculture/src/aqua/web/templates/cost.html`
- Modify: `yantai-aquaculture/src/aqua/web/build.py`（生成 cost.html，内嵌 COST_DEFAULTS）
- Modify: `yantai-aquaculture/tests/test_build.py`（补 cost 断言）

**Interfaces:**
- Consumes: `config.COST_DEFAULTS`
- Produces: `costcalc.calc_cost(inputs: dict) -> dict`，返回 `{苗费, 饲料费, 总成本, 预计产量, 保本价}`（全部保留 2 位小数）

- [ ] **Step 1: 写失败测试**

`tests/test_costcalc.py`:
```python
from aqua import costcalc


def test_calc_cost():
    r = costcalc.calc_cost({
        "miao_wan": 30, "miao_price": 120, "feed_price": 4.5,
        "feed_ratio": 1.2, "elec": 3000, "med": 2000, "other": 5000,
        "survival": 0.7, "size_jin": 0.055,
    })
    # 产量 = 30万尾 * 0.7 * 0.055斤 = 11550 斤
    assert r["预计产量"] == 11550.0
    # 苗费 3600 + 饲料 11550*1.2*4.5=62370 + 电3000 + 药2000 + 其他5000
    assert r["总成本"] == 75970.0
    assert round(r["保本价"], 2) == 6.58  # 75970 / 11550


def test_calc_cost_zero_output():
    r = costcalc.calc_cost({"miao_wan": 0, "miao_price": 120,
                            "feed_price": 4.5, "feed_ratio": 1.2,
                            "elec": 0, "med": 0, "other": 0,
                            "survival": 0.7, "size_jin": 0.055})
    assert r["保本价"] == 0
```

- [ ] **Step 2: 运行测试确认失败 → 实现 costcalc.py → 运行测试确认通过**

`src/aqua/costcalc.py`:
```python
"""成本模型：保本价计算。"""
def calc_cost(i: dict) -> dict:
    output = i["miao_wan"] * 10000 * i["survival"] * i["size_jin"]  # 斤
    miao = i["miao_wan"] * i["miao_price"]
    feed = output * i["feed_ratio"] * i["feed_price"]
    total = miao + feed + i["elec"] + i["med"] + i["other"]
    breakeven = round(total / output, 2) if output > 0 else 0
    return {"苗费": round(miao, 2), "饲料费": round(feed, 2),
            "总成本": round(total, 2), "预计产量": round(output, 2),
            "保本价": breakeven}
```

- [ ] **Step 3: 实现 cost.html 模板**

`src/aqua/web/templates/cost.html`（九个输入框默认值来自 `__COST_DEFAULTS__`，JS 前端完成与 costcalc 相同的算式，输出保本价大字 + 分项明细）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>保本价计算</title>
<style>
  body { margin: 0; font-family: system-ui, "Microsoft YaHei", sans-serif;
         background: #f5f6f8; }
  header { background: #14532d; color: #fff; padding: 12px 16px;
           font-size: 18px; font-weight: 600; }
  .card { background: #fff; margin: 10px 12px; border-radius: 10px;
          padding: 14px; }
  .row { display: flex; align-items: center; margin: 8px 0; }
  .row label { width: 100px; font-size: 14px; flex-shrink: 0; }
  .row input { flex: 1; font-size: 16px; padding: 8px; border: 1px solid #ccc;
               border-radius: 6px; min-width: 0; }
  .row .unit { width: 78px; font-size: 12px; color: #888; text-align: right; }
  button { width: 100%; margin-top: 14px; padding: 12px; font-size: 16px;
           background: #14532d; color: #fff; border: 0; border-radius: 8px; }
  #result { margin-top: 14px; font-size: 15px; line-height: 1.9; }
  .big { font-size: 24px; font-weight: 700; color: #14532d; }
  .note { font-size: 12px; color: #999; margin-top: 10px; }
  nav { display: flex; justify-content: space-around; background: #fff;
        padding: 10px 0; border-top: 1px solid #eee; font-size: 14px;
        position: sticky; bottom: 0; }
  a { color: #14532d; text-decoration: none; }
</style>
</head>
<body>
<header>保本价计算</header>
<div class="card">
  <div class="row"><label>投苗量</label>
    <input type="number" id="miao_wan"><span class="unit">万尾</span></div>
  <div class="row"><label>苗价</label>
    <input type="number" id="miao_price"><span class="unit">元/万尾</span></div>
  <div class="row"><label>饲料单价</label>
    <input type="number" id="feed_price" step="0.1"><span class="unit">元/斤</span></div>
  <div class="row"><label>饲料系数</label>
    <input type="number" id="feed_ratio" step="0.1"><span class="unit">斤料/斤虾</span></div>
  <div class="row"><label>电费</label>
    <input type="number" id="elec"><span class="unit">元</span></div>
  <div class="row"><label>药费</label>
    <input type="number" id="med"><span class="unit">元</span></div>
  <div class="row"><label>其他费用</label>
    <input type="number" id="other"><span class="unit">元</span></div>
  <div class="row"><label>成活率</label>
    <input type="number" id="survival" step="0.05"><span class="unit">0~1</span></div>
  <div class="row"><label>出虾规格</label>
    <input type="number" id="size_jin" step="0.005"><span class="unit">斤/尾</span></div>
  <button onclick="calc()">计算保本价</button>
  <div id="result"></div>
  <div class="note">示例默认值仅供参考，请按实际投入调整。保本价 = 总成本 ÷ 预计产量。</div>
</div>
<nav>
  <a href="index.html">行情</a><a href="forecast.html">预测</a>
  <a href="news.html">新闻</a><a href="cost.html">成本</a>
  <a href="guide.html">新手</a>
</nav>
<script>
const DEFAULTS = __COST_DEFAULTS__;
["miao_wan","miao_price","feed_price","feed_ratio","elec","med","other",
 "survival","size_jin"].forEach(k => {
  document.getElementById(k).value = DEFAULTS[k];
});

function calc() {
  const g = id => parseFloat(document.getElementById(id).value) || 0;
  const miao = g("miao_wan") * g("miao_price");
  const output = g("miao_wan") * 10000 * g("survival") * g("size_jin");
  const feed = output * g("feed_ratio") * g("feed_price");
  const total = miao + feed + g("elec") + g("med") + g("other");
  const breakeven = output > 0 ? total / output : 0;
  document.getElementById("result").innerHTML =
    `<div class="big">保本价 ${breakeven.toFixed(2)} 元/斤</div>
     <div>预计产量 ${output.toFixed(0)} 斤</div>
     <div>总成本 ${total.toFixed(0)} 元
       （苗 ${miao.toFixed(0)} / 饲料 ${feed.toFixed(0)}
        / 电 ${g("elec")} / 药 ${g("med")} / 其他 ${g("other")}）</div>`;
}
</script>
</body>
</html>
```

- [ ] **Step 4: build.py 生成 cost.html（内嵌 `__COST_DEFAULTS__`）+ 补测试跑绿**

- [ ] **Step 5: 构建并手动验证 + 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 保本价成本计算器"
```

---

### Task 14: 新手内容（养殖时间轴 + 避坑清单）

**Files:**
- Create: `yantai-aquaculture/src/aqua/web/templates/guide.html`
- Modify: `yantai-aquaculture/src/aqua/web/build.py`（复制生成 guide.html，无数据占位）

**Interfaces:** 无（纯静态内容页）

- [ ] **Step 1: 用 WebSearch 调研并写内容**

调研要点：山东南美白虾养殖流程（放苗时间、标粗、水质管理）、暂养皮皮虾/梭子蟹保活要点、生蚝肥美期与加工注意、新手常见坑（病害防治不当、密度过高、缺氧、出虾时机）。**所有事实性内容必须有可查证来源，宁缺毋假。**

guide.html 结构：
- 顶部：一年养殖时间轴（横向滚动卡片：1-12 月，每月标注"该做什么 + 当月价格规律"）
- 中段：三个业务板块（虾养殖 / 蟹虾暂养 / 生蚝加工）各 5-8 条关键要点
- 末段：新手避坑清单（10 条，每条一句场景 + 一句对策）
- 底部声明："内容依据公开资料整理，具体操作请结合本地老师傅经验"

- [ ] **Step 2: 构建验证页面手机可读 + 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 新手内容页"
```

---

### Task 15: 月报一页纸生成

**Files:**
- Create: `yantai-aquaculture/src/aqua/web/report.py`
- Create: `yantai-aquaculture/src/aqua/web/templates/report.html`
- Create: `yantai-aquaculture/tests/test_report.py`

**Interfaces:**
- Consumes: `db.price_series`、`db.import_by_month`、`db.news_list`、`config.HOLIDAYS`、`forecast.window_stats`
- Produces: `report.generate(db_path, ym, out_dir) -> str`（返回生成文件路径，文件名为 `月报-YYYY-MM.html`）

- [ ] **Step 1: 写失败测试**

`tests/test_report.py`:
```python
from aqua import db
from aqua.web import report


def test_generate_report(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.upsert_price(conn, {"species": "白虾", "date": "2026-09-01",
                           "price": 22.0, "price_low": None,
                           "price_high": None, "source": "test",
                           "market": "海阳", "unit": "元/斤"})
    db.upsert_news(conn, {"date": "2026-09-20", "category": "病害",
                          "title": "测试", "summary": "", "url": "",
                          "source": "test"})
    conn.commit()
    path = report.generate(str(tmp_path / "t.db"), "2026-09", str(tmp_path))
    html = open(path, encoding="utf-8").read()
    assert "2026年9月" in html and "白虾" in html and "测试" in html
```

- [ ] **Step 2: 运行测试确认失败 → 实现 report.py + report.html → 跑绿**

report.py 逻辑：读库 → 计算各品种当月均价 vs 上月 vs 去年同期（`window_stats` 可复用于"当月"窗口）→ 本月新闻列表 → 进口量 → 用 report.html 模板（A4 友好、微信直接可发）渲染输出。
模板要点：标题"海产行情月报 YYYY年M月"；三品种价格表（当月均价/环比/同比）；本月要闻列表；一句话点评（模板句式，执行时人工补写）。

- [ ] **Step 3: 生成 2026-09 样例月报并验收**

```bash
python -c "from aqua.web import report; print(report.generate('yantai-aquaculture/data/aquarium.db', '2026-09', 'yantai-aquaculture/site'))"
```

- [ ] **Step 4: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "新增: 月报一页纸生成"
```

---

### Task 16: 总验收与交付说明

- [ ] **Step 1: 全量测试** `pytest` 全绿；`pipeline.run` + `build.build` 顺序真实执行一遍无错
- [ ] **Step 2: 写 README.md**（项目简介、目录结构、更新命令两条、页面清单、已知数据缺口：皮皮虾稀疏、进口量为人工月度、全国口径≠海阳价）
- [ ] **Step 3: 按"分里程碑验收"清单与用户逐项确认，收集修改意见并修复**
- [ ] **Step 4: 提交**

```bash
git -C /e/ClaudeCode add yantai-aquaculture
git -C /e/ClaudeCode commit -m "文档: README与验收收尾"
```

**一期验收标准：** site/ 五个页面手机可看；预测器/计算器交互可用；pipeline+build 两条命令可重复运行；月报样例产出；维护手册清晰。

---

## 附录：执行顺序与依赖

M1（T1-T6，顺序执行）→ M2（T7-T8）→ M3（T9-T10）→ M4（T11-T12）→ M5（T13-T16）。
T7 依赖 T1/T6；T9 依赖 T1；T10 依赖 T7/T9；T11 依赖 T1/T7；T13 依赖 T1/T7；T15 依赖 T1/T9。
