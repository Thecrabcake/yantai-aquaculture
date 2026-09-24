"""抓取辅助：请求与 fixture 存取。"""
import pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parents[3]  # yantai-aquaculture/
FIXTURES = ROOT / "fixtures"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}


def get(url: str, timeout: int = 30, retries: int = 3) -> str:
    """带重试的 GET，网络抖动时自动退避重试。"""
    import time

    last = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def save_fixture(name: str, text: str) -> None:
    FIXTURES.mkdir(exist_ok=True)
    (FIXTURES / name).write_text(text, encoding="utf-8")


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")
