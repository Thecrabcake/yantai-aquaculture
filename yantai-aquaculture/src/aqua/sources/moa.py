"""农业农村部月度批发价数据源（经 zjbhi.com 转载）。

每月一篇《YYYY年M月水产品价格…》，含虾蟹类/贝类大类均价与海关进口量。
品种级价格不在该源内，由 huinong 源补充。
"""
import re

from .. import db, normalize
from . import base

LIST_URL = "http://zjbhi.com/zh/cms/data/9-c.html"
MONTH_RE = re.compile(r"<title>(\d{4})年(\d{1,2})月")
CATEGORIES = ("虾蟹类", "贝类")


def _plain(text: str) -> str:
    """去脚本/样式/标签/空白，得到连续纯文本。"""
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", "", text)


def parse(text: str) -> list[dict]:
    """解析月报文章 → 大类价格记录（已统一元/斤）。"""
    m = MONTH_RE.search(text)
    if not m:
        raise ValueError("无法从标题提取年月")
    date = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-15"
    plain = _plain(text)
    records = []
    for cat in CATEGORIES:
        pm = re.search(rf"{cat}加权平均批发价每公斤(\d+\.?\d*)元", plain)
        if not pm:
            continue
        records.append({
            "species": cat,
            "date": date,
            "price": normalize.to_yuan_per_jin(float(pm.group(1)), "元/公斤"),
            "price_low": None,
            "price_high": None,
            "source": "moa",
            "market": "全国批发市场均价",
            "unit": "元/斤",
        })
    return records


def parse_import(text: str) -> dict | None:
    """提取文中海关进口数据（水产品总量，万吨→吨）。"""
    m = MONTH_RE.search(text)
    if not m:
        return None
    article_y, article_m = int(m.group(1)), int(m.group(2))
    plain = _plain(text)
    pm = re.search(r"(\d{1,2})月份我国水产品进口(\d+\.?\d*)万吨", plain)
    if not pm:
        return None
    data_m = int(pm.group(1))
    year = article_y if data_m <= article_m else article_y - 1
    return {"ym": f"{year:04d}-{data_m:02d}",
            "product": "水产品",
            "volume_ton": float(pm.group(2)) * 10000,
            "source": "moa"}


def _find_articles(pages: int = 40) -> list[str]:
    """翻列表页收集《…水产品价格…》文章链接，翻完或到 pages 上限为止。"""
    urls = []
    fail_streak = 0
    for page in range(1, pages + 1):
        try:
            text = base.get(f"{LIST_URL}?page={page}")
        except Exception as e:
            fail_streak += 1
            print(f"[moa] 列表第{page}页失败: {e}")
            if fail_streak >= 3:
                break  # 连续失败视为翻到头
            continue
        fail_streak = 0
        ids = re.findall(r"9-c/(\d+)-a\.html", text)
        if not ids:
            break  # 翻到头了
        found = re.findall(
            r'href="([^"]*9-c/\d+-a\.html)"[^>]*>\s*([^<]*水产品价格[^<]*)',
            text)
        urls.extend(f"http://zjbhi.com{u}" for u, _ in found)
    return urls


def run(conn) -> int:
    n = 0
    for url in _find_articles():
        try:
            text = base.get(url)
            for rec in parse(text):
                db.upsert_price(conn, rec)
                n += 1
            imp = parse_import(text)
            if imp:
                db.upsert_import(conn, imp)
        except Exception as e:
            print(f"[moa] {url} 失败: {e}")
    conn.commit()
    return n
