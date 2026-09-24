"""品种级价格：人工周度录入 JSON → 入库。

周度品种行情（白虾/皮皮虾/梭子蟹/生蚝）没有可直接爬取的行情站，
报价散见于市场新闻报道。由维护者每周从新闻/问价中收集数条报价，
写进 data/price_manual.json（含 name/date/price/unit/market/source）。
记录宁缺毋假：只录有明确日期和来源的价格。
"""
import json
import pathlib

from .. import db, normalize

DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[3] / "data" / "price_manual.json"


def run(conn, path=None) -> int:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    if not p.exists():
        print(f"[manual_price] 未找到 {p}，跳过（首次运行先建立该文件）")
        return 0
    data = json.loads(p.read_text(encoding="utf-8"))
    for rec in data:
        db.upsert_price(conn, normalize.normalize_record(rec))
    conn.commit()
    return len(data)
