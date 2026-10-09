#!/usr/bin/env python3
# collect sina 7x24 realtime financial news, dedup, tag related watchlist, append to 消息面/
import json, urllib.request, os, sys, datetime

ROOT = sys.argv[1]
CN = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
DATE = CN.strftime("%Y-%m-%d")
NOW = CN.strftime("%H:%M")
NEWS = os.path.join(ROOT, "消息面")
os.makedirs(NEWS, exist_ok=True)
SEEN = os.path.join(NEWS, ".seen_ids.txt")
seen = set()
if os.path.exists(SEEN):
    seen = {l.strip() for l in open(SEEN, encoding="utf-8") if l.strip()}

# sina 7x24 realtime API (live feed, updates every minute)
API = "https://app.cj.sina.com.cn/api/news/pc?page=1&num=200"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
      "Referer": "https://finance.sina.com.cn/7x24/"}

# keyword -> related watchlist tag (ASCII names from tools/watchlist.txt)
KEYMAP = [
    ("华为", "华为链:ZTE/000063,Tuowei/002261,Changshan/000158,DigitalChina/000034"),
    ("鸿蒙", "华为链:ZTE/000063"),
    ("中兴", "ZTE/000063"),
    ("黄金", "黄金:ChifengGold/600988,HunanGold/002155"),
    ("金价", "黄金:ChifengGold/600988,HunanGold/002155"),
    ("石油", "石油:CNOOC/600938,Zhongman/603619,Guanghui/600256"),
    ("原油", "石油:CNOOC/600938,Zhongman/603619,Guanghui/600256"),
    ("油气", "石油:CNOOC/600938,Zhongman/603619,Guanghui/600256"),
    ("汽车", "汽车/新能源:BYD/002594,AutoETF/516110,NEVETF/515030"),
    ("新能源", "新能源:BYD/002594,CATL/300750,NEVETF/515030,NewEnergyETF/516160"),
    ("比亚迪", "BYD/002594"),
    ("宁德", "CATL/300750"),
    ("半导体", "半导体:ChipETF/512760,SemiETF/512480,GigaDevice/603986"),
    ("芯片", "半导体:ChipETF/512760,SemiETF/512480"),
    ("光刻", "半导体:SemiETF/512480"),
    ("通信", "通信:TelecomETF/515880,ZTE/000063"),
    ("5G", "通信:TelecomETF/515880"),
    ("光模块", "光模块:Innolight/300308,Eoptolink/300502"),
    ("中际旭创", "Innolight/300308"),
    ("新易盛", "Eoptolink/300502"),
    ("电力", "电力:Mengdian/600863,Wanneng/000543,Huaneng/600011,LeshanPower/600644"),
    ("银行", "银行:BankETF/512800"),
    ("券商", "券商:BrokerETF/512880"),
    ("证券", "券商:BrokerETF/512880"),
    ("科创", "科创:STAR50ETF/588000"),
    ("创业板", "创业:ChiNextETF/159915"),
    ("白酒", "酒:LiquorETF/512690,Wuliangye/000858"),
    ("酒", "酒:LiquorETF/512690"),
    ("消费", "消费:Haier/600690,Gree/000651,Wuliangye/000858"),
    ("光伏", "光伏:SolarETF/515790,NewEnergyETF/516160"),
    ("太阳能", "光伏:SolarETF/515790"),
    ("军工", "军工:DefenseETF/512660"),
    ("国防", "军工:DefenseETF/512660"),
    ("传媒", "传媒:MediaETF/512980"),
    ("有色", "有色:MetalETF/512400"),
    ("金属", "有色:MetalETF/512400"),
    ("科技", "科技:TechETF/515000"),
    ("恒瑞", "Hengrui/600276"),
    ("药明", "WuXiAppTec/603259"),
    ("创新药", "医药:PharmaETF/512010,HealthETF/512170"),
    ("医药", "医药:PharmaETF/512010,HealthETF/512170"),
    ("CRO", "医药:WuXiAppTec/603259"),
    ("海尔", "Haier/600690"),
    ("格力", "Gree/000651"),
    ("五粮液", "Wuliangye/000858"),
    ("AI", "AI:算力/光模块/半导体链"),
    ("算力", "算力:光模块/数据中心"),
    ("机器人", "机器人:拓维/常山/中兴"),
    ("低空", "低空经济:通信/军工"),
    ("重组", "重组概念:个股事件驱动"),
    ("并购", "并购概念:个股事件驱动"),
]


def tag(title):
    hits = []
    for kw, t in KEYMAP:
        if kw in title:
            hits.append(t)
    seen_t = set()
    out = []
    for h in hits:
        if h not in seen_t:
            seen_t.add(h)
            out.append(h)
    return out


new_items = []
try:
    req = urllib.request.Request(API, headers=UA)
    data = json.load(urllib.request.urlopen(req, timeout=20))
    feed = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
except Exception as e:
    print(f"ERR {e}")
    sys.exit(0)

for x in feed:
    nid = str(x.get("id", ""))
    if not nid or nid in seen:
        continue
    seen.add(nid)
    title = (x.get("rich_text", "") or "").replace("\n", " ").strip()
    ctime = x.get("create_time", "") or ""
    tags = tag(title)
    rel = ", ".join(tags) if tags else "—"
    line = f"- [{ctime}] {title}  \n  - 涉及: {rel}  \n  - 来源: 新浪7x24 | id={nid}"
    new_items.append((ctime, line))

new_items.sort(key=lambda a: a[0])
daily = os.path.join(NEWS, f"{DATE}.md")
if not os.path.exists(daily):
    open(daily, "w", encoding="utf-8").write(f"# news 7x24 {DATE}\n")

with open(SEEN, "w", encoding="utf-8") as f:
    f.write("\n".join(list(seen)[-8000:]) + "\n")

if new_items:
    with open(daily, "a", encoding="utf-8") as f:
        f.write(f"\n## {NOW} (新增 {len(new_items)})\n")
        for _, line in new_items:
            f.write(line + "\n")
    print(len(new_items))
else:
    print(0)
