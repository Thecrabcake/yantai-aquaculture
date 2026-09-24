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
