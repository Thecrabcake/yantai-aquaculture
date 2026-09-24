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
