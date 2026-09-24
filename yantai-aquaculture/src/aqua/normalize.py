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
