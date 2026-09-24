"""惠农网产地行情：每日品种报价表（服务端渲染，可爬）。

行情页（cnhnb.com/hangqing/cdlist-{频道ID}-...）为表格：
日期 | 品名 | 产地 | 价格元/斤 | 涨跌幅，每日更新。
每个品种频道聚合成一个区间点（中位数/最低/最高）入库。
当前确认频道：生蚝 2001458；白虾/皮皮虾/梭子蟹频道 ID 待从惠农网
APP 分类树补充，找到后加入 CHANNELS 即可。
"""
import re
from statistics import median
from .. import db
from . import base

CHANNELS = {"生蚝": "2001458"}


def parse(text: str, species: str) -> dict | None:
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if not m:
        return None
    vals = [float(v) for v in re.findall(r"(\d+\.?\d*)元/斤", text)]
    if not vals:
        return None
    return {
        "species": species,
        "date": m.group(1),
        "price": round(median(vals), 2),
        "price_low": round(min(vals), 2),
        "price_high": round(max(vals), 2),
        "source": "huinong",
        "market": "惠农网产地行情",
        "unit": "元/斤",
    }


def run(conn) -> int:
    n = 0
    for species, cid in CHANNELS.items():
        try:
            text = base.get(
                f"https://www.cnhnb.com/hangqing/cdlist-{cid}-0-0-0-0-1/")
            rec = parse(text, species)
            if rec:
                db.upsert_price(conn, rec)
                n += 1
            else:
                print(f"[huinong] {species} 频道无报价数据")
        except Exception as e:
            print(f"[huinong] {species} 失败: {e}")
    conn.commit()
    return n
