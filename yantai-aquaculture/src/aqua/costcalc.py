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
