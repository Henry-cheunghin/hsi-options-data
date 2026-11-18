<!DOCTYPE html>
<html lang="zh-HK">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>恒指四大方向實戰分析總表 (2026-11-19 星期四 · 11/18 結算更新版)</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <style>
    body {
      font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: #0f172a;
      color: #f8fafc;
    }
    .glass-card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 0.75rem;
    }
    .alert-banner {
      background: linear-gradient(90deg, rgba(225, 29, 72, 0.30), rgba(15, 23, 42, 0.96));
      border: 1px solid rgba(244, 63, 94, 0.8);
      border-radius: 0.75rem;
    }
    .badge-bull { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-bear { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }
    .badge-warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-info { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #334155; padding: 12px 14px; text-align: left; vertical-align: top; }
    th { background-color: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
    tr:hover td { background-color: rgba(51, 65, 85, 0.35); }
  </style>
</head>
<body class="p-3 sm:p-6 max-w-6xl mx-auto space-y-5">

  <!-- Mandatory Rule 0 Directional Alert Banner -->
  <div class="alert-banner p-4 sm:p-5 shadow-lg">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="text-sm sm:text-base font-black text-rose-400">
        🚨🚨【極端級別機構單邊睇淡警報 · 即月淨數單日暴增 +4,872 張】
      </div>
      <span class="px-2.5 py-0.5 rounded text-xs font-bold badge-bear">嚴禁撈底買升 · 順勢高空為主</span>
    </div>
    <p class="text-xs sm:text-sm text-slate-200 mt-2 leading-relaxed">
      11/18 結算數據全面確認機構強力造淡：<strong>(1)</strong> 即月期指（NOV-26）<strong>未平倉總數大增 +3,390 張</strong>至 121,352 張，<strong>未平倉淨數更單日暴增 +4,872 張</strong>至 40,310 張；<strong>(2)</strong> 原重兵 23,400 Put 牆減倉 <strong>-190 張</strong>撤退，大戶改於 <strong>23,400 Call (+185 張)</strong> 壓頂；<strong>(3)</strong> 23:44 夜期已插穿 23,100 殺牛區至 <strong>23,129</strong>（低見 23,097，低水 166 點）。
    </p>
  </div>

  <!-- Header -->
  <header class="glass-card p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4">
    <div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold badge-info">HSI Trading System · 11/18 晚間結算完整數據</span>
        <span class="text-xs text-slate-400">數據來源：投創教育 HKIEI ＋ 港交所 (23:44 HKT)</span>
      </div>
      <h1 class="text-xl sm:text-2xl font-black text-white mt-1.5">恒指四大核心方向與六大輔助指標實戰總表 (2026-11-19 星期四)</h1>
    </div>
    <div class="flex flex-wrap gap-3 text-xs">
      <div class="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-700">
        <div class="text-slate-400">11/18 現貨 / 日市期指結算</div>
        <div class="text-base font-bold text-rose-400">23,294.75 / 23,226 <span class="text-xs">(低水 69)</span></div>
      </div>
      <div class="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-700">
        <div class="text-slate-400">11/18 夜期 (23:44 HKT)</div>
        <div class="text-base font-bold text-rose-400">23,129 <span class="text-xs">(-361 · 低水 166 點)</span></div>
      </div>
    </div>
  </header>

  <!-- Quick Filter Tabs -->
  <div class="flex flex-wrap gap-2 text-xs">
    <button onclick="filterRows('all')" id="tabAll" class="px-3 py-1.5 rounded-lg font-bold bg-sky-600 text-white">📋 全部項目 (10項)</button>
    <button onclick="filterRows('core')" id="tabCore" class="px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700">🎯 三大核心方向 (1–3)</button>
    <button onclick="filterRows('aux')" id="tabAux" class="px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700">🧭 六大輔助驗證 (4.1–4.6)</button>
    <button onclick="filterRows('plan')" id="tabPlan" class="px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700">⚡ 週四實戰劇本</button>
  </div>

  <!-- Master Structured Table -->
  <section class="glass-card overflow-hidden shadow-xl">
    <div class="overflow-x-auto">
      <table id="forecastTable" class="text-xs sm:text-sm">
        <thead>
          <tr>
            <th class="w-36 sm:w-44">分析維度 / 項目</th>
            <th class="w-52 sm:w-64">11/18 最新真實結算數據</th>
            <th class="w-28">多空偏向</th>
            <th>實戰解讀與操作啟示</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800">
          <!-- Pillar 1 -->
          <tr class="row-item" data-cat="core">
            <td class="font-bold text-sky-300">
              1. 未平倉框架<br>
              <span class="text-[11px] font-normal text-slate-400">NOV-26 期權鏈 (HKIEI)</span>
            </td>
            <td class="space-y-1">
              <div><span class="text-rose-400 font-bold">Call 天花板：</span>24,000 (<strong>1,671</strong>, +80) / 24,400 (1,128, -2) / 23,400 (707, <span class="text-rose-300 font-bold">+185</span>)</div>
              <div><span class="text-emerald-400 font-bold">Put 牆下移：</span><strong>23,000 (1,381, +483)</strong> / <strong>22,800 (1,257, +420)</strong> / 22,000 (1,191, +143)</div>
              <div class="text-[11px] text-slate-400">原 23,400 Put 減至 992 (-190) · 23,000 Put 成交 1,210 張</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">重心下移 23,000</span></td>
            <td class="text-slate-200 leading-relaxed">
              大戶於 <strong>23,400 Put (-190張)</strong> 及 23,600 Put (-62張) 止蝕撤退，同時喺 <strong>23,400 Call (+185張)</strong> 壓頂，並將下方重兵防線全面退守至 <strong>23,000 (1,381張)</strong> 及 <strong>22,800 (1,257張)</strong>！
            </td>
          </tr>

          <!-- Pillar 2 -->
          <tr class="row-item" data-cat="core">
            <td class="font-bold text-sky-300">
              2. 每週波幅預計方向<br>
              <span class="text-[11px] font-normal text-slate-400">週一起點原則</span>
            </td>
            <td class="space-y-1">
              <div><strong>週一起點：</strong>23,708 (現貨) / 23,678 (期指)</div>
              <div><strong>本週至今高低：</strong>23,890 (11/16) / <strong>23,097</strong> (11/18夜期)</div>
              <div><strong>已行波幅：</strong><strong>793 點</strong> (目標 800–1,100 點)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">起點下衝刺</span></td>
            <td class="text-slate-200 leading-relaxed">
              夜期跌見 23,097 後，本週累積波幅已達 <strong>793 點</strong>，正逼近 800–1,100 點目標下限（對應 <strong>23,090 至 22,790</strong>），完全符合「起點之下睇跌直至達標」原則。
            </td>
          </tr>

          <!-- Pillar 3 -->
          <tr class="row-item" data-cat="core">
            <td class="font-bold text-sky-300">
              3. 期指未平倉總數/淨數<br>
              <span class="text-[11px] font-normal text-slate-400">11/18 結算實數 (HKIEI)</span>
            </td>
            <td class="space-y-1">
              <div><strong>11月總數：</strong><strong>121,352</strong> (<span class="text-rose-400 font-bold">+3,390 張</span>)</div>
              <div><strong>11月淨數：</strong><strong>40,310</strong> (<span class="text-rose-400 font-bold">+4,872 張</span>)</div>
              <div class="text-[11px] text-slate-400">11/18 現貨 -213.42 / 期指收 23,226 (-264)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">大戶狂加空倉</span></td>
            <td class="text-slate-200 leading-relaxed">
              極罕見強力睇淡訊號！今日跌市之下，即月總數大增 <strong>+3,390 張</strong>，淨數更單日狂飆 <strong>+4,872 張</strong>（超越 +800 張警報線 6 倍），代表大戶及機構正全力開新空單落去，完全唔似見底！
            </td>
          </tr>

          <!-- Aux 4.1 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.1 黃金比率<br>
              <span class="text-[11px] font-normal text-slate-400">22,943 至 24,897</span>
            </td>
            <td class="space-y-1">
              <div>76.4% 防線：<span class="text-rose-400">23,404 (已失守轉鐵阻)</span></div>
              <div>100% 起漲底：<strong class="text-sky-300">22,943</strong></div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">直逼 100% 底</span></td>
            <td class="text-slate-200 leading-relaxed">
              失守 76.4%（23,404）後跌勢加速，夜期 23,129 距離 100% 起漲底 <strong>22,943</strong> 僅餘約 186 點。
            </td>
          </tr>

          <!-- Aux 4.2 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.2 波浪理論<br>
              <span class="text-[11px] font-normal text-slate-400">Elliott Wave 浪型</span>
            </td>
            <td class="space-y-1">
              <div>A 浪：24,897 ➜ 23,562 (1,335點)</div>
              <div>B 浪：23,562 ➜ 23,890</div>
              <div>C 浪延伸：23,890 ➜ 23,097 (進行中)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">C 浪加速段</span></td>
            <td class="text-slate-200 leading-relaxed">
              C 浪正朝 0.618–0.764 倍等幅目標（<strong>23,065 至 22,870</strong>）進發，在淨空倉單日 +4,872 張壓力下仍未見轉折底。
            </td>
          </tr>

          <!-- Aux 4.3 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.3 牛熊證重貨區<br>
              <span class="text-[11px] font-normal text-slate-400">打靶殺牛/屠熊位</span>
            </td>
            <td class="space-y-1">
              <div><strong>今早重牛區：</strong>23,100–23,199 (662張, +300)</div>
              <div><strong>下層重牛區：</strong><strong>22,700–22,799 (704張)</strong> (<a href="https://www.i-cable.com/category/%E8%B2%A1%E7%B6%93%E8%B3%87%E8%A8%8A/%E8%82%A1%E5%B8%82%E7%9B%B4%E6%92%AD%E5%AE%A4" target="_blank" class="underline hover:text-sky-300">有線新聞</a>)</div>
              <div><strong>熊證重貨：</strong>24,000–24,099 (735張)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">23,100 即殺</span></td>
            <td class="text-slate-200 leading-relaxed">
              夜期 23,129（低見 23,097）令 <strong>23,100–23,199 牛證（662張）</strong> 明早 09:30 開市即面臨全數收回；下一個大牛群集中於 <strong>22,700–22,799</strong>。
            </td>
          </tr>

          <!-- Aux 4.4 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.4 最近期高低位<br>
              <span class="text-[11px] font-normal text-slate-400">波段座標</span>
            </td>
            <td class="space-y-1">
              <div><strong>11/18 期指日市：</strong>開 23,484 / 高 23,540 / 低 23,202 / 收 23,226</div>
              <div><strong>11/18 夜期 (23:44)：</strong>高 23,231 / 低 <strong>23,097</strong> / 現報 <strong>23,129</strong></div>
              <div><strong>前低大底：</strong>22,943 (11/2)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">續創新低</span></td>
            <td class="text-slate-200 leading-relaxed">
              夜期低水 166 點且跌破日市低位 23,202，日市低位 <strong>23,202–23,231</strong> 明日將轉為即市反彈首關阻力。
            </td>
          </tr>

          <!-- Aux 4.5 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.5 大戶嘅 P&amp;L<br>
              <span class="text-[11px] font-normal text-slate-400">Max Pain 利潤區</span>
            </td>
            <td class="space-y-1">
              <div><strong>Max Pain：</strong>24,000 (<a href="https://hsi-options-data.pages.dev/" target="_blank" class="underline hover:text-sky-300">雲端表</a>)</div>
              <div><strong>Put 牆新重倉：</strong>23,000 (1,381張) / 22,800 (1,257張)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">23,000 保衛戰</span></td>
            <td class="text-slate-200 leading-relaxed">
              做市商在 23,400 以下負 Gamma 對沖尚未完結，要到 <strong>22,800–23,000</strong>（合計 2,638 張 Put 牆）先有機會見到實質護盤阻力。
            </td>
          </tr>

          <!-- Aux 4.6 -->
          <tr class="row-item" data-cat="aux">
            <td class="font-bold text-amber-300">
              4.6 外圍、北水與宏觀<br>
              <span class="text-[11px] font-normal text-slate-400">資金流與業績</span>
            </td>
            <td class="space-y-1">
              <div><strong>騰訊(00700)Q3：</strong>AI資本開支 814 億、自由現金流轉負 691 億 (<a href="https://hao.cnyes.com/post/278710" target="_blank" class="underline hover:text-sky-300">鉅亨號</a>)</div>
              <div><strong>美股(11/18早段)：</strong>道指跌逾 400 點 (-1%) / 標指 -0.48% (<a href="https://www.hk01.com/%E8%B2%A1%E7%B6%93%E5%BF%AB%E8%A8%8A/60412431/%E7%BE%8E%E8%82%A1-%E9%81%93%E6%8C%87%E6%97%A9%E6%AE%B5%E8%B7%8C%E9%80%BE400%E9%BB%9E-%E7%B4%8D%E6%8C%87%E9%9D%A0%E7%A9%A9" target="_blank" class="underline hover:text-sky-300">HK01</a>)</div>
              <div><strong>北水(11/18)：</strong>淨買入 &gt;20 億港元 (<a href="https://www.nbd.com.cn/articles/2026-11-18/4651051.html" target="_blank" class="underline hover:text-sky-300">每日經濟新聞</a>)</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">騰訊+美股壓盤</span></td>
            <td class="text-slate-200 leading-relaxed">
              騰訊業績後市場憂慮高資本開支蠶食短期利潤，疊加美股道指早段續跌逾 400 點，拖累港股夜期大低水。
            </td>
          </tr>

          <!-- Action Plan -->
          <tr class="row-item bg-slate-800/60" data-cat="plan">
            <td class="font-bold text-rose-300">
              ⚡ 週四最新實戰劇本<br>
              <span class="text-[11px] font-normal text-slate-400">+300止賺 / -100止蝕</span>
            </td>
            <td class="space-y-1">
              <div><strong>反抽高空區：</strong>23,200–23,260 (止蝕 23,330)</div>
              <div><strong>下探目標：</strong>22,900–23,000 (+300點止賺)</div>
              <div><strong>嚴禁撈底線：</strong>未見 22,800–23,000 企穩前不開多</div>
            </td>
            <td><span class="px-2 py-0.5 rounded text-xs font-bold badge-bear">高空不撈底</span></td>
            <td class="text-slate-100 leading-relaxed">
              1. <strong>淨數 +4,872 張鐵證下絕不逆勢接飛刀：</strong>明早殺完 23,100 牛證後切勿急於買升。<br>
              2. <strong>順勢高空劇本：</strong>若早盤殺牛後技術反抽 <strong>23,200–23,260</strong>（今日日市收市及低水回補區）受阻，順勢開空（-100 點止蝕放 23,330，目標 +300 點看 <strong>22,900–22,950</strong>）。<br>
              3. <strong>觀察底線：</strong>只有當指數回踩 <strong>22,800–23,000</strong>（新 Put 重兵＋本週 1,000 點波幅達標區）並出現止跌陽燭，先再評估博反彈。
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <script>
    function filterRows(cat) {
      const rows = document.querySelectorAll('.row-item');
      rows.forEach(r => {
        if (cat === 'all' || r.dataset.cat === cat) {
          r.style.display = '';
        } else {
          r.style.display = 'none';
        }
      });
      const btns = {
        all: document.getElementById('tabAll'),
        core: document.getElementById('tabCore'),
        aux: document.getElementById('tabAux'),
        plan: document.getElementById('tabPlan')
      };
      Object.keys(btns).forEach(k => {
        if (k === cat) {
          btns[k].className = 'px-3 py-1.5 rounded-lg font-bold bg-sky-600 text-white';
        } else {
          btns[k].className = 'px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700';
        }
      });
    }
  </script>
</body>
</html>
