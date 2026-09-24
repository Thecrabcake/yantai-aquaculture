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
