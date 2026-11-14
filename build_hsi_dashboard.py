import datetime
import glob
import json
import os
import re
import sys
import time
import pandas as pd
from playwright.sync_api import sync_playwright


def to_num(val):
    if val is None or val == "":
        return 0
    return float(str(val).replace(",", "").replace("%", "").strip())


def format_diff(val, force_sign=True):
    if val is None:
        return '<span class="text-slate-500">-</span>'
    val = int(val)
    if val > 0:
        prefix = "+" if force_sign else ""
        return f'<span class="text-rose-400 font-bold">{prefix}{val:,}</span>'
    elif val < 0:
        return f'<span class="text-emerald-400 font-bold">{val:,}</span>'
    return '<span class="text-slate-400">0</span>'


def parse_hsif_report(report_text):
    """解析港交所官方期指每日報告 (hsifYYMMDD.htm) 取得即月/下月/季月/總數之未平倉總數及官方升跌"""
    lines = report_text.splitlines()
    month_pattern = re.compile(r"^\s*((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s-]\d{2})(?!/)")
    total_pattern = re.compile(r"All\s+Contracts\s+Total", re.IGNORECASE)

    contracts = []
    official_total = None

    for line in lines:
        m = month_pattern.search(line)
        if m:
            nums = [int(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*", line[m.end():])]
            if len(nums) >= 4:
                gross_oi = nums[-2]
                change_oi = nums[-1]
                if gross_oi >= 0:
                    contracts.append({
                        "month": m.group(1).replace(" ", "-"),
                        "gross": gross_oi,
                        "change": change_oi,
                    })
        elif total_pattern.search(line):
            nums = [int(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*", line)]
            if len(nums) >= 3:
                official_total = {
                    "gross": nums[-2],
                    "change": nums[-1],
                }

    return contracts, official_total


def parse_hsio_net_by_month(report_text):
    """解析港交所官方期權每日報告 (hsioYYMMDD.htm)，計算各月份 Put 總未平倉減 Call 總未平倉之淨數"""
    lines = report_text.splitlines()
    month_header = re.compile(r"\b((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s-]\d{2})\b")
    strike_row = re.compile(r"^\s*(\d{4,5})\s+([CP])\b")

    current_mon = None
    mon_cp = {}

    for line in lines:
        # 偵測月份區塊標題（非行使價明細行）
        if not strike_row.match(line):
            mh = month_header.search(line)
            if mh and ("CALL" in line.upper() or "PUT" in line.upper() or "CONTRACT" in line.upper() or len(line.strip()) <= 25):
                current_mon = mh.group(1).replace(" ", "-")
                if current_mon not in mon_cp:
                    mon_cp[current_mon] = {"C": 0, "P": 0}
                continue

        sr = strike_row.match(line)
        if sr and current_mon:
            cp_type = sr.group(2)
            nums = [int(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*", line[sr.end():])]
            # hsio 明細行倒數第 2 個數字為未平倉合約 (OI)，倒數第 1 個為升跌
            if len(nums) >= 2 and nums[-2] >= 0:
                mon_cp[current_mon][cp_type] += nums[-2]

    return {m: (v["P"] - v["C"]) for m, v in mon_cp.items() if (v["C"] + v["P"]) > 0}


def fetch_latest_hkex_data():
    opt_url = "https://www.hkex.com.hk/Market-Data/Futures-and-Options-Prices/Equity-Index/Hang-Seng-Index-Futures-and-Options?sc_lang=zh-HK"
    is_cloud = os.environ.get("GITHUB_ACTIONS") == "true" or sys.platform != "win32"
    print(f"🚀 正在連接港交所官方系統抓取最新數據 (雲端模式: {is_cloud})...")
    all_widget_urls = []
    hsif_reports = []
    hsio_reports = []

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
        page.goto(opt_url, wait_until="domcontentloaded", timeout=60000)
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

        today = datetime.datetime.now()
        for delta in range(8):
            d = today - datetime.timedelta(days=delta)
            if d.weekday() >= 5:
                continue
            yymmdd = d.strftime("%y%m%d")

            if len(hsif_reports) < 1:
                try:
                    txt_f = page.evaluate(
                        """async (u) => { const r = await fetch(u); return r.ok ? await r.text() : ""; }""",
                        f"https://www.hkex.com.hk/eng/stat/dmstat/dayrpt/hsif{yymmdd}.htm",
                    )
                    if txt_f and "ALL CONTRACTS TOTAL" in txt_f.upper():
                        print(f"📄 成功讀取港交所官方期指報告：hsif{yymmdd}.htm")
                        hsif_reports.append((yymmdd, txt_f))
                except Exception:
                    pass

            if len(hsio_reports) < 2:
                try:
                    txt_o = page.evaluate(
                        """async (u) => { const r = await fetch(u); return r.ok ? await r.text() : ""; }""",
                        f"https://www.hkex.com.hk/eng/stat/dmstat/dayrpt/hsio{yymmdd}.htm",
                    )
                    if txt_o and "OPEN INTEREST" in txt_o.upper():
                        print(f"📄 成功讀取港交所官方期權報告：hsio{yymmdd}.htm")
                        hsio_reports.append((yymmdd, txt_o))
                except Exception:
                    pass

            if len(hsif_reports) >= 1 and len(hsio_reports) >= 2:
                break

        browser.close()

    all_data["_hsif_reports"] = hsif_reports
    all_data["_hsio_reports"] = hsio_reports
    return all_data


def build_combined_breakdown(hsif_reports, hsio_reports, spot_call_oi, spot_put_oi, prev_summary):
    mon_order = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

    def sort_mon(m):
        p = m.split("-")
        return (int(p[1]), mon_order.get(p[0], 99))

    bd = {
        "spot": {"label": "即月", "gross": 0, "gross_diff": None, "net": None, "net_diff": None},
        "next": {"label": "下月", "gross": 0, "gross_diff": None, "net": None, "net_diff": None},
        "quarter": {"label": "季月", "gross": 0, "gross_diff": None, "net": None, "net_diff": None},
        "total": {"label": "總數", "gross": 0, "gross_diff": None, "net": None, "net_diff": None},
    }

    # 1. 填充期指未平倉總數 (Gross OI) 及升跌
    unique_contracts = []
    if hsif_reports:
        cur_contracts, cur_total = parse_hsif_report(hsif_reports[0][1])
        seen = set()
        for c in cur_contracts:
            if c["month"] not in seen:
                seen.add(c["month"])
                unique_contracts.append(c)

        for idx, c in enumerate(unique_contracts):
            if idx == 0:
                bd["spot"]["label"] = f"即月 ({c['month']})"
                bd["spot"]["gross"] = c["gross"]
                bd["spot"]["gross_diff"] = c["change"]
            elif idx == 1:
                bd["next"]["label"] = f"下月 ({c['month']})"
                bd["next"]["gross"] = c["gross"]
                bd["next"]["gross_diff"] = c["change"]
            else:
                bd["quarter"]["gross"] += c["gross"]
                bd["quarter"]["gross_diff"] = (bd["quarter"]["gross_diff"] or 0) + c["change"]

        if cur_total and cur_total["gross"] > 0:
            bd["total"]["gross"] = cur_total["gross"]
            bd["total"]["gross_diff"] = cur_total["change"]
        else:
            bd["total"]["gross"] = bd["spot"]["gross"] + bd["next"]["gross"] + bd["quarter"]["gross"]
            bd["total"]["gross_diff"] = (bd["spot"]["gross_diff"] or 0) + (bd["next"]["gross_diff"] or 0) + (bd["quarter"]["gross_diff"] or 0)

    # 2. 填充各月份未平倉淨數 (Put - Call) 並與上個交易日相減計出淨數升/跌
    cur_net_map = parse_hsio_net_by_month(hsio_reports[0][1]) if hsio_reports else {}
    prev_net_map = parse_hsio_net_by_month(hsio_reports[1][1]) if len(hsio_reports) >= 2 else {}

    if cur_net_map:
        mons = sorted(cur_net_map.keys(), key=sort_mon)
        for idx, m in enumerate(mons):
            n_val = cur_net_map[m]
            p_val = prev_net_map.get(m)
            if idx == 0:
                if bd["spot"]["label"] == "即月":
                    bd["spot"]["label"] = f"即月 ({m})"
                bd["spot"]["net"] = n_val
                if p_val is not None:
                    bd["spot"]["net_diff"] = n_val - p_val
            elif idx == 1:
                if bd["next"]["label"] == "下月":
                    bd["next"]["label"] = f"下月 ({m})"
                bd["next"]["net"] = n_val
                if p_val is not None:
                    bd["next"]["net_diff"] = n_val - p_val
            else:
                bd["quarter"]["net"] = (bd["quarter"]["net"] or 0) + n_val
                if p_val is not None:
                    bd["quarter"]["net_diff"] = (bd["quarter"]["net_diff"] or 0) + (n_val - p_val)
    else:
        # 備用：使用即時即月 Put - Call 並與本地上日快照相減
        bd["spot"]["net"] = spot_put_oi - spot_call_oi
        if prev_summary and "breakdown" in prev_summary:
            p_spot = prev_summary["breakdown"].get("spot", {}).get("net")
            if p_spot is not None:
                bd["spot"]["net_diff"] = bd["spot"]["net"] - int(p_spot)

    # 計算總數淨數及總數淨數升跌
    net_parts = [bd[k]["net"] for k in ["spot", "next", "quarter"] if bd[k]["net"] is not None]
    if net_parts:
        bd["total"]["net"] = sum(net_parts)

    diff_parts = [bd[k]["net_diff"] for k in ["spot", "next", "quarter"] if bd[k]["net_diff"] is not None]
    if diff_parts:
        bd["total"]["net_diff"] = sum(diff_parts)
    elif prev_summary and "breakdown" in prev_summary and bd["total"]["net"] is not None:
        p_tot = prev_summary["breakdown"].get("total", {}).get("net")
        if p_tot is not None:
            bd["total"]["net_diff"] = bd["total"]["net"] - int(p_tot)

    return bd


def load_previous_day_data(today_tag):
    os.makedirs("history_data", exist_ok=True)
    files = sorted(glob.glob("history_data/HSI_Options_*.csv"))
    prev_files = [f for f in files if today_tag not in os.path.basename(f)]
    if not prev_files:
        return None
    latest_prev = prev_files[-1]
    try:
        prev_df = pd.read_csv(latest_prev)
        return prev_df.set_index("strike").to_dict("index")
    except Exception:
        return None


def load_previous_summary(today_tag):
    files = sorted(glob.glob("history_data/HSI_Summary_*.json"))
    prev_files = [f for f in files if today_tag not in os.path.basename(f)]
    if not prev_files:
        return None
    try:
        with open(prev_files[-1], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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
    today_tag = datetime.datetime.now().strftime("%Y%m%d")
    prev_map = load_previous_day_data(today_tag)
    prev_summary = load_previous_summary(today_tag)

    rows = []
    for item in opt_list:
        strike = int(to_num(item.get("strike")))
        c = item.get("c", {})
        p = item.get("p", {})

        c_oi = int(to_num(c.get("oi")))
        c_vol = int(to_num(c.get("vo")))
        p_oi = int(to_num(p.get("oi")))
        p_vol = int(to_num(p.get("vo")))

        if prev_map and strike in prev_map:
            prev_row = prev_map[strike]
            prev_c_oi = int(to_num(prev_row.get("call_oi", 0)))
            prev_c_vol = int(to_num(prev_row.get("call_vol", 0)))
            prev_p_oi = int(to_num(prev_row.get("put_oi", 0)))
            prev_p_vol = int(to_num(prev_row.get("put_vol", 0)))

            c_oi_diff = c_oi - prev_c_oi
            c_vol_diff = c_vol - prev_c_vol
            p_oi_diff = p_oi - prev_p_oi
            p_vol_diff = p_vol - prev_p_vol
        else:
            prev_c_oi = None
            prev_c_vol = None
            prev_p_oi = None
            prev_p_vol = None
            c_oi_diff = None
            c_vol_diff = None
            p_oi_diff = None
            p_vol_diff = None

        rows.append(
            {
                "call_iv": c.get("iv", "-"),
                "call_vol_diff": c_vol_diff,
                "prev_call_vol": prev_c_vol,
                "call_vol": c_vol,
                "call_oi_diff": c_oi_diff,
                "prev_call_oi": prev_c_oi,
                "call_oi": c_oi,
                "strike": strike,
                "put_oi": p_oi,
                "prev_put_oi": prev_p_oi,
                "put_oi_diff": p_oi_diff,
                "put_vol": p_vol,
                "prev_put_vol": prev_p_vol,
                "put_vol_diff": p_vol_diff,
                "put_iv": p.get("iv", "-"),
            }
        )

    df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)

    total_call_oi = int(df["call_oi"].sum())
    total_put_oi = int(df["put_oi"].sum())
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

    bd = build_combined_breakdown(
        data.get("_hsif_reports", []),
        data.get("_hsio_reports", []),
        total_call_oi,
        total_put_oi,
        prev_summary,
    )

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
            "breakdown": bd,
            "top_call_walls": top_calls,
            "top_put_walls": top_puts,
        },
        "option_chain": df.where(pd.notnull(df), None).to_dict("records"),
    }

    with open("latest_hsi_options.json", "w", encoding="utf-8") as f:
        json.dump(api_payload, f, ensure_ascii=False, indent=2)
    df.to_csv("latest_hsi_options.csv", index=False, encoding="utf-8-sig")
    df.to_csv(f"history_data/HSI_Options_{today_tag}.csv", index=False, encoding="utf-8-sig")
    with open(f"history_data/HSI_Summary_{today_tag}.json", "w", encoding="utf-8") as f:
        json.dump(api_payload["metrics"], f, ensure_ascii=False, indent=2)

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
        row_bg = (
            "bg-amber-500/20 border-y border-amber-400/50"
            if is_atm
            else ("bg-purple-500/15" if is_mp else "hover:bg-slate-800/60")
        )
        badge = ""
        if is_atm:
            badge += '<span class="ml-1 px-1.5 py-0.5 text-[10px] bg-amber-500 text-slate-950 font-bold rounded">現價</span>'
        if is_mp:
            badge += '<span class="ml-1 px-1.5 py-0.5 text-[10px] bg-purple-500 text-white font-bold rounded">MP</span>'

        prev_c_oi_txt = f"{int(r['prev_call_oi']):,}" if pd.notnull(r["prev_call_oi"]) else "-"
        prev_c_vol_txt = f"{int(r['prev_call_vol']):,}" if pd.notnull(r["prev_call_vol"]) else "-"
        prev_p_oi_txt = f"{int(r['prev_put_oi']):,}" if pd.notnull(r["prev_put_oi"]) else "-"
        prev_p_vol_txt = f"{int(r['prev_put_vol']):,}" if pd.notnull(r["prev_put_vol"]) else "-"

        c_oi_diff_html = format_diff(r["call_oi_diff"] if pd.notnull(r["call_oi_diff"]) else None)
        c_vol_diff_html = format_diff(r["call_vol_diff"] if pd.notnull(r["call_vol_diff"]) else None)
        p_oi_diff_html = format_diff(r["put_oi_diff"] if pd.notnull(r["put_oi_diff"]) else None)
        p_vol_diff_html = format_diff(r["put_vol_diff"] if pd.notnull(r["put_vol_diff"]) else None)

        table_rows_html += f"""
        <tr class="border-b border-slate-800 text-xs sm:text-sm {row_bg}">
            <td class="py-2 px-1.5 text-right font-mono text-slate-400 hidden lg:table-cell">{r['call_iv']}%</td>
            <td class="py-2 px-1.5 text-right font-mono hidden md:table-cell">{c_vol_diff_html}</td>
            <td class="py-2 px-1.5 text-right font-mono text-slate-400 hidden lg:table-cell">{prev_c_vol_txt}</td>
            <td class="py-2 px-1.5 text-right font-mono text-slate-300 hidden sm:table-cell">{int(r['call_vol']):,}</td>
            <td class="py-2 px-1.5 text-right font-mono">{c_oi_diff_html}</td>
            <td class="py-2 px-1.5 text-right font-mono text-slate-400 hidden md:table-cell">{prev_c_oi_txt}</td>
            <td class="py-2 px-2 text-right font-mono relative bg-rose-950/20">
                <div class="absolute right-0 top-1 bottom-1 bg-rose-500/30 rounded-l" style="width:{c_pct}%"></div>
                <span class="relative z-10 font-bold text-rose-300">{int(r['call_oi']):,}</span>
            </td>

            <td class="py-2 px-2.5 text-center font-mono font-extrabold text-white bg-slate-900 border-x border-slate-700 whitespace-nowrap">
                {s:,}{badge}
            </td>

            <td class="py-2 px-2 text-left font-mono relative bg-emerald-950/20">
                <div class="absolute left-0 top-1 bottom-1 bg-emerald-500/30 rounded-r" style="width:{p_pct}%"></div>
                <span class="relative z-10 font-bold text-emerald-300">{int(r['put_oi']):,}</span>
            </td>
            <td class="py-2 px-1.5 text-left font-mono text-slate-400 hidden md:table-cell">{prev_p_oi_txt}</td>
            <td class="py-2 px-1.5 text-left font-mono">{p_oi_diff_html}</td>
            <td class="py-2 px-1.5 text-left font-mono text-slate-300 hidden sm:table-cell">{int(r['put_vol']):,}</td>
            <td class="py-2 px-1.5 text-left font-mono text-slate-400 hidden lg:table-cell">{prev_p_vol_txt}</td>
            <td class="py-2 px-1.5 text-left font-mono hidden md:table-cell">{p_vol_diff_html}</td>
            <td class="py-2 px-1.5 text-left font-mono text-slate-400 hidden lg:table-cell">{r['put_iv']}%</td>
        </tr>
        """

    call_wall_html = "".join(
        [
            f'<div class="flex justify-between text-sm py-1 border-b border-slate-800/60"><span class="font-mono font-bold text-rose-400">{x["strike"]:,}</span><span class="font-mono text-slate-200">{x["call_oi"]:,} 張</span></div>'
            for x in top_calls
        ]
    )
    put_wall_html = "".join(
        [
            f'<div class="flex justify-between text-sm py-1 border-b border-slate-800/60"><span class="font-mono font-bold text-emerald-400">{x["strike"]:,}</span><span class="font-mono text-slate-200">{x["put_oi"]:,} 張</span></div>'
            for x in top_puts
        ]
    )

    def render_summary_row(key, is_total=False):
        item = bd[key]
        row_style = "bg-sky-950/80 font-extrabold text-amber-300 border-t border-sky-700/70" if is_total else "border-b border-slate-800/70 text-slate-200"
        gross_txt = f"{item['gross']:,}" if item["gross"] > 0 else "-"
        net_txt = f"{item['net']:+,}" if item["net"] is not None else "-"
        return f"""
        <tr class="{row_style} text-xs sm:text-sm">
            <td class="py-1.5 px-4 text-left font-semibold text-sky-300">{item['label']}</td>
            <td class="py-1.5 px-4 text-right font-mono font-bold">{gross_txt}</td>
            <td class="py-1.5 px-4 text-right font-mono border-r border-slate-700">{format_diff(item['gross_diff'])}</td>
            <td class="py-1.5 px-4 text-right font-mono font-bold">{net_txt}</td>
            <td class="py-1.5 px-4 text-right font-mono">{format_diff(item['net_diff'])}</td>
        </tr>
        """

    summary_rows_html = (
        render_summary_row("spot")
        + render_summary_row("next")
        + render_summary_row("quarter")
        + render_summary_row("total", is_total=True)
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-HK" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>恒生指數期權未平倉大數據監控 | HKEX 官方實戰版</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
    <div class="max-w-[1440px] mx-auto px-3 sm:px-6 py-6">
        <header class="flex flex-col md:flex-row md:items-center md:justify-between pb-5 border-b border-slate-800 gap-4">
            <div>
                <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-white">恒生指數期權 (HSI Options) 未平倉分布</h1>
                <p class="text-xs sm:text-sm text-slate-400 mt-1">數據源：香港交易所 (HKEX) 官方系統 ｜ 最後更新：<span class="text-amber-400 font-mono">{last_upd}</span> ｜ API：<a href="./latest_hsi_options.json" class="underline text-sky-400">JSON</a> / <a href="./latest_hsi_options.csv" class="underline text-sky-400">CSV</a></p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-right">
                <div class="text-xs text-slate-400">恒生指數最新 / 收市</div>
                <div class="text-xl font-mono font-bold text-white">{hsi_spot:,.2f} <span class="text-xs font-normal text-slate-300">{hsi_change}</span></div>
            </div>
        </header>

        <!-- 核心決策卡片 -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-5">
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
                <div class="text-xs text-slate-400 uppercase tracking-wider">即月期權 Put/Call 比率 (PCR)</div>
                <div class="text-3xl font-mono font-extrabold text-amber-400 mt-2">{pcr}</div>
                <div class="text-xs text-slate-300 mt-2 font-mono">即月 Call: {total_call_oi:,} ｜ Put: {total_put_oi:,}</div>
            </div>
        </section>

        <!-- 釘死在視窗頂端的【單一簡潔格仔：未平倉總數(期指) & 未平倉淨數(期權P-C) 及各自升跌】＋【Call/Put雙層欄位表頭】 -->
        <div class="sticky top-0 z-30 shadow-2xl bg-slate-950">
            <div class="bg-slate-900 border-t border-x border-sky-700/70 rounded-t-2xl overflow-hidden">
                <table class="w-full border-collapse">
                    <thead>
                        <tr class="bg-sky-950/90 text-xs text-sky-300 border-b border-sky-800/70">
                            <th class="py-1.5 px-4 text-left font-bold w-1/5">合約月份</th>
                            <th class="py-1.5 px-4 text-right font-bold w-1/5">未平倉總數 (期指)</th>
                            <th class="py-1.5 px-4 text-right font-bold w-1/5 border-r border-slate-700">總數升/跌</th>
                            <th class="py-1.5 px-4 text-right font-bold w-1/5">未平倉淨數 (期權P-C)</th>
                            <th class="py-1.5 px-4 text-right font-bold w-1/5">淨數升/跌</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_rows_html}
                    </tbody>
                </table>
            </div>

            <table class="w-full border-collapse table-fixed">
                <thead>
                    <tr class="text-xs sm:text-sm font-bold tracking-wider border-y border-slate-700">
                        <th colspan="7" class="py-2 px-2 text-center bg-indigo-900 text-white border-r border-slate-700">Call（認購期權 · 上方阻力）</th>
                        <th class="py-2 px-2 text-center bg-slate-950 text-amber-400 w-24 sm:w-28">行使價</th>
                        <th colspan="7" class="py-2 px-2 text-center bg-sky-900 text-white border-l border-slate-700">Put（認沽期權 · 下方支持）</th>
                    </tr>
                    <tr class="bg-slate-800 text-[11px] sm:text-xs text-slate-100 border-b-2 border-slate-600 whitespace-nowrap">
                        <th class="py-2 px-1.5 text-right hidden lg:table-cell">IV</th>
                        <th class="py-2 px-1.5 text-right hidden md:table-cell">成交增減</th>
                        <th class="py-2 px-1.5 text-right hidden lg:table-cell">上日成交</th>
                        <th class="py-2 px-1.5 text-right hidden sm:table-cell">成交</th>
                        <th class="py-2 px-1.5 text-right">未平倉增減</th>
                        <th class="py-2 px-1.5 text-right hidden md:table-cell">上日未平倉</th>
                        <th class="py-2 px-2 text-right text-rose-300 font-extrabold bg-rose-950/60">未平倉</th>

                        <th class="py-2 px-2 text-center bg-slate-950 font-mono text-white w-24 sm:w-28">STRIKE</th>

                        <th class="py-2 px-2 text-left text-emerald-300 font-extrabold bg-emerald-950/60">未平倉</th>
                        <th class="py-2 px-1.5 text-left hidden md:table-cell">上日未平倉</th>
                        <th class="py-2 px-1.5 text-left">未平倉增減</th>
                        <th class="py-2 px-1.5 text-left hidden sm:table-cell">成交</th>
                        <th class="py-2 px-1.5 text-left hidden lg:table-cell">上日成交</th>
                        <th class="py-2 px-1.5 text-left hidden md:table-cell">成交增減</th>
                        <th class="py-2 px-1.5 text-left hidden lg:table-cell">IV</th>
                    </tr>
                </thead>
            </table>
        </div>

        <section class="bg-slate-900/90 border-x border-b border-slate-800 rounded-b-2xl shadow-2xl">
            <table class="w-full border-collapse table-fixed">
                <colgroup>
                    <col class="hidden lg:table-column">
                    <col class="hidden md:table-column">
                    <col class="hidden lg:table-column">
                    <col class="hidden sm:table-column">
                    <col>
                    <col class="hidden md:table-column">
                    <col>
                    <col class="w-24 sm:w-28">
                    <col>
                    <col class="hidden md:table-column">
                    <col>
                    <col class="hidden sm:table-column">
                    <col class="hidden lg:table-column">
                    <col class="hidden md:table-column">
                    <col class="hidden lg:table-column">
                </colgroup>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </section>
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("🎉 最終版已完成！index.html、latest_hsi_options.json、latest_hsi_options.csv 已全部更新！")


if __name__ == "__main__":
    raw_data = fetch_latest_hkex_data()
    if raw_data:
        generate_dashboard_and_api(raw_data)