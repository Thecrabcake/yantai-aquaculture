"""中国水产频道（fishfirst.cn）价格行情文章 → 品种报价点。

价格频道文章为记者走访塘口/批发市场的一线报价（"20头约18元/斤"式），
每篇按品种聚合成一个区间点（中位数/最低/最高）。频道 2025 年后停更，
本源一次性回填历史；之后品种价由 manual_price 周录补充。
"""
import re
from statistics import median
from .. import db
from . import base

LIST_URL = "http://www.fishfirst.cn/price/"

# 品种判定关键词（先皮皮虾/梭子蟹/生蚝，最后白虾兜底）
def _species_of(title: str) -> str | None:
    if "皮皮虾" in title or "虾蛄" in title:
        return "皮皮虾"
    if "梭子蟹" in title or "蟹价" in title:
        return "梭子蟹"
    if "生蚝" in title or "牡蛎" in title or "蚝价" in title:
        return "生蚝"
    if "虾" in title and "小龙虾" not in title and "饲料" not in title:
        return "白虾"
    return None


def _plain(text: str) -> str:
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def parse_article(text: str, title: str) -> dict | None:
    """文章正文 → 品种区间报价记录；非品种行情文章返回 None。"""
    species = _species_of(title)
    if not species:
        return None
    plain = _plain(text)
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", plain)
    if not m:
        return None
    # 去掉涨跌幅描述（"跌4元/斤""涨2元/斤"不是价格）
    plain = re.sub(r"[跌涨降](?:幅|价)?(?:达|至|了)?\s*\d+\.?\d*(?:-\d+\.?\d*)?元/斤",
                   " ", plain)
    vals = [float(v) for v in re.findall(r"(\d+\.?\d*)(?:-\d+\.?\d*)?元/斤", plain)
            if 5 <= float(v) <= 200]
    if not vals:
        return None
    return {
        "species": species,
        "date": f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
        "price": round(median(vals), 2),
        "price_low": round(min(vals), 2),
        "price_high": round(max(vals), 2),
        "source": "fishfirst",
        "market": "塘口/批发走访（多地区）",
        "unit": "元/斤",
    }


def _fetch_list() -> list[tuple[str, str]]:
    """价格频道列表 → [(文章URL, 标题)]，翻页直到内容重复。"""
    seen_pages = set()
    found = []
    page = 1
    while page < 20:
        url = LIST_URL if page == 1 else f"{LIST_URL}index_{page}.html"
        text = base.get(url)
        if text in seen_pages:
            break  # 分页参数被忽略时终止
        seen_pages.add(text)
        arts = re.findall(
            r'href="(http://www\.fishfirst\.cn/article-\d+-1\.html)"[^>]*>([^<]{6,60})</a>',
            text)
        for href, title in arts:
            if _species_of(title) and (href, title.strip()) not in found:
                found.append((href, title.strip()))
        page += 1
    return found


def run(conn) -> int:
    n = 0
    for url, title in _fetch_list():
        try:
            rec = parse_article(base.get(url), title)
            if rec:
                db.upsert_price(conn, rec)
                n += 1
        except Exception as e:
            print(f"[fishfirst] {url} 失败: {e}")
    conn.commit()
    return n
