import datetime
import json
import os
import sys
import time
import pandas as pd
from playwright.sync_api import sync_playwright


def to_num(val):
    if val is None or val == "":
        return 0
    return float(str(val).replace(",", "").replace("%", "").strip())


def fetch_latest_hkex_data():
    url = "https://www.hkex.com.hk/Market-Data/Futures-and-Options-Prices/Equity-Index/Hang-Seng-Index-Futures-and-Options?sc_lang=zh-HK"
    is_cloud = os.environ.get("GITHUB_ACTIONS") == "true" or sys.platform != "win32"
    print(f"🚀 正在連接港交所官方系統抓取最新恒指期權數據 (雲端無頭模式: {is_cloud})...")
    all_widget_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_cloud,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        def on_request(request):
            if "hkexwidget/data/" in request.url:
                all_widget_urls.append(request.url)

        page.on("request", on_request)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        try:
            opt_tab = page.locator("text=期權").first
            if opt_tab.is_visible():
                opt_tab.click()
                time.sleep(4)
        except Exception:
            pass

        for _ in range(6):
            time.sleep(1.5)
            page.mouse.wheel(0, 700)
        time.sleep(3)

        unique_urls = list(dict.fromkeys(all_widget_urls))
        all_data = {}
        for idx, u in enumerate(unique_urls):
            short_name = u.split("hkexwidget/data/")[1].split("?")[0]
            if short_name in ["getderivativesoption", "getmarketmarquee"]:
                key_name = f"{short_name}_{idx}"
                try:
                    raw_text = page.evaluate(
                        """async (targetUrl) => {
                            const res = await fetch(targetUrl);
                            return await res.text();
                        }""",
                        u,
                    )
                    s = raw_text.find("(")
                    e = raw_text.rfind(")")
                    if s != -1 and e != -1 and e > s:
                        all_data[key_name] = json.loads(raw_text[s + 1 : e])
                except Exception:
                    pass
        browser.close()
    return all_data


def generate_dashboard_and_api(data):
    hsi_spot = 0
    hsi_change = ""
    for k, v in data.items():
        if "getmarketmarquee" in k:
            for idx_item in v.get("data", {}).get("indices", []):
                if idx_item.get("ric") == ".HSI":
                    hsi_spot = to_num(idx_item.get("ls"))
                    hsi_change = f"{idx_item.get('nc')} ({idx_item.get('pc')}%)"

    best_opt = None
    for k, v in data.items():
        if "getderivativesoption" in k and isinstance(v, dict):
            d = v.get("data", {})
            opt_list = d.get("optionlist", [])
            if best_opt is None or len(opt_list) > len(best_opt.get("optionlist", [])):
                best_opt = d

    if not best_opt:
        print("❌ 未能獲取期權鏈數據，保留舊版網頁不覆蓋。")
        sys.exit(1)

    last_upd = best_opt.get("lastupd", datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    opt_list = best_opt.get("optionlist", [])

    rows = []
    for item in opt_list:
        strike = int(to_num(item.get("strike")))
        c = item.get("c", {})
        p = item.get("p", {})
        rows.append(
            {
                "call_oi": int(to_num(c.get("oi"))),
                "call_vol": int(to_num(c.get("vo"))),
                "call_iv": c.get("iv", "-"),
                "call_last": c.get("ls", "-"),
                "strike": strike,
                "put_last": p.get("ls", "-"),
                "put_iv": p.get("iv", "-"),
                "put_vol": int(to_num(p.get("vo"))),
                "put_oi": int(to_num(p.get("oi"))),
            }
        )

    df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)

    # 計算核心實戰指標
    total_call_oi = int(df["call_oi"].sum())
    total_put_oi = int(df["put_oi"].sum())
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

    top_calls = df.nlargest(3, "call_oi")[["strike", "call_oi"]].to_dict("records")
    top_puts = df.nlargest(3, "put_oi")[["strike", "put_oi"]].to_dict("records")

    strikes = df["strike"].values
    call_ois = df["call_oi"].values
    put_ois = df["put_oi"].values
    min_pain = float("inf")
    max_pain_strike = 0
    for s in strikes:
        pain = sum(max(0, s - k) * oi for k, oi in zip(strikes, call_ois)) + sum(
            max(0, k - s) * oi for k, oi in zip(strikes, put_ois)
        )
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = int(s)

    # 【供其他 Project 自動調用的標準 API 數據檔案】
    api_payload = {
        "source": "HKEX Official",
        "last_updated": last_upd,
        "hsi_spot": hsi_spot,
        "hsi_change": hsi_change,
        "metrics": {
            "max_pain": max_pain_strike,
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "put_call_ratio": pcr,
            "top_call_walls": top_calls,
            "top_put_walls": top_puts,
        },
        "option_chain": df.to_dict("records"),
    }

    with open("latest_hsi_options.json", "w", encoding="utf-8") as f:
        json.dump(api_payload, f, ensure_ascii=False, indent=2)
    df.to_csv("latest_hsi_options.csv", index=False, encoding="utf-8-sig")

    os.makedirs("history_data", exist_ok=True)
    today_tag = datetime.datetime.now().strftime("%Y%m%d")
    df.to_csv(f"history_data/HSI_Options_{today_tag}.csv", index=False, encoding="utf-8-sig")

    max_oi_single = max(df["call_oi"].max(), df["put_oi"].max(), 1)
    table_rows_html = ""
    for _, r in df.iterrows():
        s = int(r["strike"])
        if r["call_oi"] == 0 and r["put_oi"] == 0 and abs(s - (hsi_spot or max_pain_strike)) > 3000:
            continue

        c_pct = round((r["call_oi"] / max_oi_single) * 100, 1)
        p_pct = round((r["put_oi"] / max_oi_single) * 100, 1)
        is_atm = hsi_spot > 0 and abs(s - hsi_spot) <= 100
        is_mp = s == max_pain_strike
        row_bg = "bg-amber-500/20 border-y border-amber-400/50" if is_atm else ("bg-purple-500/15" if is_mp else "hover:bg-slate-800/60")
        badge = ""
        if is_atm:
            badge += '<span class="ml-1 px-1.5 py-0.5 text-[10px] bg-amber-500 text-slate-950 font-bold rounded">現價區</span>'
        if is_mp:
            badge += '<span class="ml-1 px-1.5 py-0.5 text-[10px] bg-purple-500 text-white font-bold rounded">MaxPain</span>'

        table_rows_html += f"""
        <tr class="border-b border-slate-800 text-xs sm:text-sm {row_bg}">
            <td class="py-2 px-2 text-right font-mono relative">
                <div class="absolute right-0 top-1 bottom-1 bg-rose-500/25 rounded-l" style="width:{c_pct}%"></div>
                <span class="relative z-10 font-semibold text-rose-300">{r['call_oi']:,}</span>
            </td>
            <td class="py-2 px-2 text-right font-mono text-slate-400 hidden sm:table-cell">{r['call_vol']:,}</td>
            <td class="py-2 px-2 text-right font-mono text-slate-400 hidden md:table-cell">{r['call_iv']}%</td>
            <td class="py-2 px-2 text-right font-mono text-slate-200">{r['call_last'] or '-'}</td>
            <td class="py-2 px-3 text-center font-mono font-bold text-white bg-slate-900/90 border-x border-slate-700">
                {s:,}{badge}
            </td>
            <td class="py-2 px-2 text-left font-mono text-slate-200">{r['put_last'] or '-'}</td>
            <td class="py-2 px-2 text-left font-mono text-slate-400 hidden md:table-cell">{r['put_iv']}%</td>
            <td class="py-2 px-2 text-left font-mono text-slate-400 hidden sm:table-cell">{r['put_vol']:,}</td>
            <td class="py-2 px-2 text-left font-mono relative">
                <div class="absolute left-0 top-1 bottom-1 bg-emerald-500/25 rounded-r" style="width:{p_pct}%"></div>
                <span class="relative z-10 font-semibold text-emerald-300">{r['put_oi']:,}</span>
            </td>
        </tr>
        """

    call_wall_html = "".join(
        [f'<div class="flex justify-between text-sm py-1 border-b border-slate-800/60"><span class="font-mono font-bold text-rose-400">{x["strike"]:,}</span><span class="font-mono text-slate-200">{x["call_oi"]:,} 張</span></div>' for x in top_calls]
    )
    put_wall_html = "".join(
        [f'<div class="flex justify-between text-sm py-1 border-b border-slate-800/60"><span class="font-mono font-bold text-emerald-400">{x["strike"]:,}</span><span class="font-mono text-slate-200">{x["put_oi"]:,} 張</span></div>' for x in top_puts]
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-HK" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>恒生指數期權未平倉大數據監控 | HKEX 官方全自動版</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
    <div class="max-w-7xl mx-auto px-4 py-6">
        <header class="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-slate-800 gap-4">
            <div>
                <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-white">恒生指數期權 (HSI Options) 未平倉分布</h1>
                <p class="text-xs sm:text-sm text-slate-400 mt-1">數據源：香港交易所 (HKEX) 官方系統 ｜ 最後更新：<span class="text-amber-400 font-mono">{last_upd}</span> ｜ API：<a href="./latest_hsi_options.json" class="underline text-sky-400">JSON</a> / <a href="./latest_hsi_options.csv" class="underline text-sky-400">CSV</a></p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-right">
                <div class="text-xs text-slate-400">恒生指數最新 / 收市</div>
                <div class="text-xl font-mono font-bold text-white">{hsi_spot:,.2f} <span class="text-xs font-normal text-slate-300">{hsi_change}</span></div>
            </div>
        </header>

        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-6">
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                <div class="text-xs text-slate-400 uppercase tracking-wider">期權最大痛點 (Max Pain)</div>
                <div class="text-3xl font-mono font-extrabold text-purple-400 mt-2">{max_pain_strike:,}</div>
                <div class="text-xs text-slate-400 mt-2">莊家結算賠付最小化核心區</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">大戶 Call 重兵阻力牆 Top 3</div>
                {call_wall_html}
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">大戶 Put 重兵支持牆 Top 3</div>
                {put_wall_html}
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                <div class="text-xs text-slate-400 uppercase tracking-wider">全月總未平倉 & Put/Call 比率</div>
                <div class="text-3xl font-mono font-extrabold text-amber-400 mt-2">{pcr}</div>
                <div class="text-xs text-slate-300 mt-2 font-mono">Call: {total_call_oi:,} ｜ Put: {total_put_oi:,}</div>
            </div>
        </section>

        <section class="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full border-collapse">
                    <thead>
                        <tr class="bg-slate-900 text-xs text-slate-300 border-b border-slate-700">
                            <th colspan="4" class="py-2.5 px-3 text-center text-rose-400 font-bold tracking-wider border-r border-slate-800">認購期權 CALL（看升 / 上方阻力）</th>
                            <th class="py-2.5 px-3 text-center bg-slate-950 text-white font-bold">行使價</th>
                            <th colspan="4" class="py-2.5 px-3 text-center text-emerald-400 font-bold tracking-wider border-l border-slate-800">認沽期權 PUT（看跌 / 下方支持）</th>
                        </tr>
                        <tr class="bg-slate-900/60 text-[11px] text-slate-400 border-b border-slate-800">
                            <th class="py-2 px-2 text-right">未平倉 (OI)</th>
                            <th class="py-2 px-2 text-right hidden sm:table-cell">成交量</th>
                            <th class="py-2 px-2 text-right hidden md:table-cell">引伸波幅</th>
                            <th class="py-2 px-2 text-right">最後價</th>
                            <th class="py-2 px-3 text-center bg-slate-950 font-mono">STRIKE</th>
                            <th class="py-2 px-2 text-left">最後價</th>
                            <th class="py-2 px-2 text-left hidden md:table-cell">引伸波幅</th>
                            <th class="py-2 px-2 text-left hidden sm:table-cell">成交量</th>
                            <th class="py-2 px-2 text-left">未平倉 (OI)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </section>
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("🎉 已生成最新網頁 index.html 及 API 數據檔 (latest_hsi_options.json / .csv)")


if __name__ == "__main__":
    raw_data = fetch_latest_hkex_data()
    if raw_data:
        generate_dashboard_and_api(raw_data)