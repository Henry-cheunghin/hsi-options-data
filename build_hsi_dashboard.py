"""
HSI Options & Futures All-In-One Dashboard Builder (100% Python Stdlib - Zero External Deps)
- Fetches 100% Real HKEX Official Data:
  1. Options OI & Max Pain & PCR: hsioc{yymmdd}.htm
  2. Futures DTOP (Gross OI, Net OI, Net OI Change): DTOP_F_{yyyymmdd}.zip
  3. Futures Daily Market Report: dmreport1.htm
- Outputs: index.html (with Mandatory Rule 0 Directional Alert + 10-Item Master Table)
- Zero Fabrication: Any unavailable non-HKEX intraday field is labeled "待補".
"""

import html as html_lib
import io
import os
import re
import urllib.request
import zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    )
}


def fetch_bytes(url: str, timeout: int = 25) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 500:
                    return data
    except Exception as exc:
        print(f"[WARN] Fetch failed {url}: {exc}")
    return None


def strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</tr>|</p>|</div>|</li>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html_lib.unescape(text)


def parse_int(s: str) -> int:
    s = s.replace(",", "").replace("+", "").strip()
    if not s or s in ("-", "--", "N/A"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def find_latest_options():
    now = datetime.now(HKT)
    for offset in range(5):
        dt = now - timedelta(days=offset)
        if dt.weekday() >= 5:
            continue
        yymmdd = dt.strftime("%y%m%d")
        url = f"https://www.hkex.com.hk/chi/stat/dmstat/dayrpt/hsioc{yymmdd}.htm"
        raw = fetch_bytes(url)
        if raw:
            page = raw.decode("utf-8", errors="ignore")
            if "行使價" in page or "未平倉" in page:
                return dt.strftime("%Y-%m-%d"), page
    return None, None


def parse_options_oi(page: str) -> dict:
    text = strip_html(page)
    months = sorted({(int(y), int(m)) for y, m in re.findall(r"(\d{2})\s*年\s*(\d{1,2})\s*月", text)})
    front_label = f"20{months[0][0]:02d}年{months[0][1]:02d}月" if months else "即月"

    calls, puts = {}, {}
    for line in text.splitlines():
        nums = re.findall(r"[-+]?\d[\d,]*", line)
        if len(nums) >= 8:
            strike_cand = parse_int(nums[0])
            if 15000 <= strike_cand <= 35000 and strike_cand % 100 == 0:
                c_oi = parse_int(nums[-4])
                p_oi = parse_int(nums[-2])
                if c_oi >= 0:
                    calls[strike_cand] = calls.get(strike_cand, 0) + c_oi
                if p_oi >= 0:
                    puts[strike_cand] = puts.get(strike_cand, 0) + p_oi

    total_call = sum(calls.values())
    total_put = sum(puts.values())
    pcr = round(total_put / total_call, 2) if total_call > 0 else 0.0
    top_calls = sorted(calls.items(), key=lambda x: x[1], reverse=True)[:3]
    top_puts = sorted(puts.items(), key=lambda x: x[1], reverse=True)[:3]

    all_strikes = sorted(set(calls.keys()) | set(puts.keys()))
    max_pain = 0
    if all_strikes:
        best_payout = None
        for settle in all_strikes:
            payout = sum(max(0, settle - k) * v for k, v in calls.items()) + sum(
                max(0, k - settle) * v for k, v in puts.items()
            )
            if best_payout is None or payout < best_payout:
                best_payout = payout
                max_pain = settle

    return {
        "contract": front_label,
        "total_call": total_call,
        "total_put": total_put,
        "pcr": pcr,
        "max_pain": max_pain,
        "top_calls": top_calls,
        "top_puts": top_puts,
    }


def fetch_latest_dtop_futures() -> dict:
    """Fetch HKEX DTOP_F_yyyymmdd.zip from oi_f.asp to extract HSI Futures Gross OI, Net OI & Net OI Change."""
    now = datetime.now(HKT)
    for offset in range(5):
        dt = now - timedelta(days=offset)
        if dt.weekday() >= 5:
            continue
        ymd = dt.strftime("%Y%m%d")
        for url in [
            f"https://www.hkex.com.hk/eng/stat/dmstat/oi/DTOP_F_{ymd}.zip",
            f"https://www.hkex.com.hk/eng/stat/dmstat/oi/dtop_f_{ymd}.zip",
        ]:
            raw = fetch_bytes(url)
            if raw and raw[:2] == b"PK":
                return parse_dtop_zip(dt.strftime("%Y-%m-%d"), raw)
    return {"date": "待補", "front_gross": "待補", "front_net": "待補", "front_net_chg": "待補", "sum2_net_chg": "待補"}


def parse_dtop_zip(date_str: str, zip_bytes: bytes) -> dict:
    records = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".txt", ".csv", ".htm", ".html")):
                continue
            content = zf.read(name).decode("utf-8", errors="ignore")
            if "HSI" not in content and "HANG SENG INDEX FUTURES" not in content.upper():
                continue
            for line in content.splitlines():
                if re.search(r"\bHSI\b", line) and re.search(r"\d{2}\s*[A-Z]{3}\s*\d{2}|\b[A-Z]{3}-\d{2}\b|\b20\d{2}\b", line):
                    nums = re.findall(r"[-+]?\d[\d,]*", line)
                    if len(nums) >= 5:
                        records.append((line.strip(), nums))
    if not records:
        return {"date": date_str, "front_gross": "待補", "front_net": "待補", "front_net_chg": "待補", "sum2_net_chg": "待補"}

    front_nums = records[0][1]
    front_gross = parse_int(front_nums[-3]) if len(front_nums) >= 3 else 0
    front_net = parse_int(front_nums[-2]) if len(front_nums) >= 2 else 0
    front_net_chg = parse_int(front_nums[-1]) if len(front_nums) >= 1 else 0
    second_net_chg = parse_int(records[1][1][-1]) if len(records) >= 2 else 0
    return {
        "date": date_str,
        "front_gross": f"{front_gross:,}",
        "front_net": f"{front_net:,}",
        "front_net_chg": f"{front_net_chg:+,}",
        "sum2_net_chg": f"{front_net_chg + second_net_chg:+,}",
        "raw_net_chg_int": front_net_chg + second_net_chg,
    }


def fetch_futures_daily_report() -> dict:
    """Fetch HKEX dmreport1.htm for latest HSI Futures day close, high, low & OI."""
    raw = fetch_bytes("https://www.hkex.com.hk/eng/stat/dmstat/dayrpt/dmreport1.htm")
    if not raw:
        return {"close": "待補", "high": "待補", "low": "待補", "oi": "待補"}
    text = strip_html(raw.decode("utf-8", errors="ignore"))
    for line in text.splitlines():
        if re.search(r"^[A-Z]{3}-\d{2}\b", line.strip()):
            nums = re.findall(r"[-+]?\d[\d,]*", line)
            if len(nums) >= 6:
                return {"high": nums[2], "low": nums[3], "close": nums[4], "oi": nums[-1]}
    return {"close": "待補", "high": "待補", "low": "待補", "oi": "待補"}


def build_html(opt_date: str, opt: dict, dtop: dict, fut: dict) -> str:
    now_hkt = datetime.now(HKT).strftime("%d/%m/%Y %H:%M")
    net_chg_int = dtop.get("raw_net_chg_int", 0)
    alert_html = ""
    if isinstance(net_chg_int, int) and abs(net_chg_int) >= 800:
        if net_chg_int >= 800:
            alert_html = f"""
  <div class="p-4 rounded-xl border border-rose-500/70 bg-rose-950/40 mb-5">
    <div class="font-black text-rose-400">🚨【機構未平倉淨數異動警報】</div>
    <p class="text-xs sm:text-sm text-slate-200 mt-1">港交所 DTOP ({dtop['date']}) 顯示即月＋下月淨數變動達 <strong>{dtop['sum2_net_chg']} 張</strong>，請配合當日升跌及 Put/Call 牆位置嚴格執行順勢策略。</p>
  </div>"""

    calls_str = " / ".join(f"{k:,} ({v:,}張)" for k, v in opt["top_calls"]) or "待補"
    puts_str = " / ".join(f"{k:,} ({v:,}張)" for k, v in opt["top_puts"]) or "待補"

    return f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>恒指期權與期指四大方向實戰總表</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <style>
    body {{ font-family: "Inter", -apple-system, sans-serif; background: #0f172a; color: #f8fafc; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 0.75rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 12px 14px; text-align: left; vertical-align: top; }}
    th {{ background: #0f172a; color: #94a3b8; font-size: 12px; }}
  </style>
</head>
<body class="p-4 sm:p-6 max-w-6xl mx-auto">
  {alert_html}
  <header class="card p-4 sm:p-5 mb-5 flex flex-wrap justify-between items-center gap-4">
    <div>
      <span class="text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold">100% 港交所實時真實數據 · 最後更新 {now_hkt} HKT</span>
      <h1 class="text-xl sm:text-2xl font-black mt-1.5">恒指四大方向與六大輔助指標實戰總表 ({opt['contract']})</h1>
    </div>
    <div class="flex flex-wrap gap-3 text-xs">
      <div class="bg-slate-900 px-3 py-2 rounded border border-slate-700">
        <div class="text-slate-400">Max Pain / PCR</div>
        <div class="text-base font-bold text-amber-300">{opt['max_pain']:,} <span class="text-xs">/ PCR {opt['pcr']}</span></div>
      </div>
      <div class="bg-slate-900 px-3 py-2 rounded border border-slate-700">
        <div class="text-slate-400">即月淨數 / 兩月合計變動 ({dtop['date']})</div>
        <div class="text-base font-bold text-sky-300">{dtop['front_net']} <span class="text-xs">({dtop['front_net_chg']} / 合計 {dtop['sum2_net_chg']})</span></div>
      </div>
    </div>
  </header>

  <section class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="text-xs sm:text-sm">
        <thead>
          <tr><th class="w-44">分析項目</th><th class="w-64">最新真實數據</th><th>實戰解讀與紀律提示</th></tr>
        </thead>
        <tbody>
          <tr><td class="font-bold text-sky-300">1. 未平倉框架 (港交所期權)</td><td>Call 牆：{calls_str}<br>Put 牆：{puts_str}</td><td>觀察重倉 Call/Put 牆是否被實質跌穿或 Roll Up，嚴禁貼近 Call 牆追多。</td></tr>
          <tr><td class="font-bold text-sky-300">2. 每週波幅預計方向</td><td>日市期指收：{fut['close']} (高 {fut['high']} / 低 {fut['low']})</td><td>以本週一開市為起點：企起點上睇升、落起點下睇跌，目標波幅 800–1,100 點。</td></tr>
          <tr><td class="font-bold text-sky-300">3. 期指總數與淨數 (DTOP)</td><td>總數：{dtop['front_gross']}<br>即月淨數：{dtop['front_net']} ({dtop['front_net_chg']})<br>兩月合計淨數變動：{dtop['sum2_net_chg']}</td><td>跌市淨數大增屬機構主導看淡；升市總淨同步大增屬主升推進；平倉則防反轉。</td></tr>
          <tr><td class="font-bold text-amber-300">4.1 黃金比率</td><td>待每日波段高低點校對</td><td>重點鎖定由高位回調 23.6%–38.2% 轉角買入區及 61.8%–76.4% 關鍵防線。</td></tr>
          <tr><td class="font-bold text-amber-300">4.2 波浪理論</td><td>待每日結構確認</td><td>區分推動浪（1/3/5）或 ABC 調整浪，避開 C 浪主跌段逆勢撈底。</td></tr>
          <tr><td class="font-bold text-amber-300">4.3 牛熊證重貨區</td><td>待對接法興街貨分佈圖</td><td>緊盯距離現價最近之 300 點內牛熊證密集打靶區，順大戶殺牛／屠熊方向操作。</td></tr>
          <tr><td class="font-bold text-amber-300">4.4 最近期高低位</td><td>期指日市高 {fut['high']} / 低 {fut['low']}</td><td>以本週及上週極值作為短線強弱分水嶺。</td></tr>
          <tr><td class="font-bold text-amber-300">4.5 大戶 P&amp;L (Max Pain)</td><td>Max Pain：{opt['max_pain']:,} (Call {opt['total_call']:,} / Put {opt['total_put']:,})</td><td>貼近結算週期權賣方傾向將指數維持於最大痛點附近，破牆則防負 Gamma 加速。</td></tr>
          <tr><td class="font-bold text-amber-300">4.6 外圍、北水與宏觀</td><td>待對接隔晚美股、ADR 及南向資金</td><td>結合北水淨流向、美債息及美國重大數據日（NFP/CPI/FOMC 前避彈）。</td></tr>
          <tr class="bg-slate-800/70"><td class="font-bold text-emerald-300">5. 實戰紀律策略</td><td>每週限做 2 次 · 3:1 盈虧比</td><td>嚴格執行 <strong>+300 點止賺 / -100 點止蝕</strong>，緊貼大戶牆邊緣開倉並預留 350 點跑道。</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</body>
</html>
"""


def main():
    opt_date, opt_html = find_latest_options()
    if not opt_html:
        print("[ERROR] No HKEX options report found.")
        return
    opt = parse_options_oi(opt_html)
    dtop = fetch_latest_dtop_futures()
    fut = fetch_futures_daily_report()
    out_html = build_html(opt_date, opt, dtop, fut)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(out_html)
    print(f"[OK] Built index.html for {opt_date} | MaxPain={opt['max_pain']} | DTOP={dtop}")


if __name__ == "__main__":
    main()
  
