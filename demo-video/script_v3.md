# Demo Video Script v3: Community Safety Resource Planner

- 线上网址：https://community-safety-resource-planner-dso576.streamlit.app/
- 核对时间：2026-11-08；线上版本 `0.3.0-mvp`，代码版本 `22f6621324d6`
- 所有数字都来自线上网站（默认日期 2025-01-01 至 2026-09-19）
- v3 按实测语速重写：第 2 段原稿 70 词读了约 50 秒，即每秒约 1.4 词；本稿共 390 词，纯讲解约 4 分 39 秒，加上操作停顿，成片预计约 5 分钟
- 屏幕上显示精确数字，讲解里部分大数字说成整数（如 about 179,000），念起来更顺
- 录屏窗口 1440×900；放大和高亮只在后期加，画面里的数字都是 app 真实跑出来的

| 段落 | 内容 | 预计时长 |
|---|---|---|
| 1 | 开场：用户和决策 | 0:35 |
| 2 | 总览 KPI | 0:33 |
| 3 | 排名表、分数和地图 | 0:40 |
| 4 | 交互：只选 Central | 0:30 |
| 5 | District Evidence | 0:42 |
| 6 | Compare Districts | 0:30 |
| 7 | 困难案例 | 0:35 |
| 8 | 下载、方法页和局限 | 0:34 |
| | **合计（纯讲解）** | **约 4:39** |

---

## 1. 开场：用户和决策（约 35 秒）

**屏幕操作**
1. 打开首页，停在顶部标题 "Streetlight Assessment"
2. 高亮 "Not a causal finding" 提示框
3. 高亮 "Streetlight data unavailable" 提示框

**讲解**
> This is our Community Safety Resource Planner. Our user is a program manager at the LA Bureau of Street Lighting, deciding which LAPD reporting districts get an on-site lighting assessment first. The app sets assessment priority only. It doesn't predict anything, and it doesn't show that lighting causes offenses.

---

## 2. 总览 KPI（约 33 秒）

**屏幕操作**
1. 依次高亮顶部三个标签："Data through September 19, 2026"、"Nighttime 18:00–05:59"
2. 高亮左侧日期筛选（2025-01-01 至 2026-09-19）
3. 依次高亮四个 KPI 卡片：179,209 / 1,164 / 90.4% / 178,921

**讲解**
> The overview counts nighttime reported offenses, 6 p.m. to 6 a.m., from January 2025 to September 2026. That's about 179,000 offenses in 1,164 districts. Persistence is 90%: a typical district has nighttime reports in nine of every ten months. And almost every offense can be mapped.

---

## 3. 排名表、分数和地图（约 40 秒）

**屏幕操作**
1. 向下滚动到 "Ranked reporting districts (top 10 of 1,164 eligible)"
2. 高亮第 1 行：0182 · Central · near S Flower St，分数 87.68，1,167 条，21/21，Recent 147
3. 展开 "Score detail: percentiles behind the priority score"，高亮公式
4. 向下滚动到地图 "Mapped nighttime reported offenses, overview districts"，停 3 秒

**讲解**
> The ranked table shows which districts to assess first. The score, from 0 to 100, is 60% frequency, how many reports, and 40% persistence, how many months they appear in, so one short spike can't reach the top. District 0182 in Central ranks first, at 87.68. The map shows where these reports are; darker means more.

---

## 4. 交互：只选 Central（约 30 秒）

**屏幕操作**
1. 左侧取消勾选 "All areas"
2. 在 "Areas" 里点选 "Central"（直接点选项，不按回车）
3. 画面回到顶部，依次高亮 KPI：14,249 / 56 / 90.6% / 14,226
4. 高亮表格第 1 行：0182 分数 86.07
5. 地图同步缩小到 Central，停 2 秒
6. 点 "Reset all to defaults"，数字回到 179,209

**讲解**
> The filters update everything together. With only Central selected, we get 56 districts and about 14,000 offenses. 0182 is still first, but its score drops to 86.07, because it's now compared with Central districts only, not the whole city. Now I'll reset.

---

## 5. District Evidence（约 42 秒）

**屏幕操作**
1. 回到 Priority Overview 表格，点第 1 行的勾选框（0182）
2. 切到 "District Evidence"，高亮 KPI：rank 1、87.68、1,167、21 / 21、100.0%
3. 滚动到月度折线图，高亮最后一个点和灰色 "Partial month" 区域
4. 滚动到 Offense composition 条形图，高亮第一条（459 BFMV，222，19.0%）
5. 滚动到 Premise composition 条形图，高亮 "Parking Lot / Garage / Drop Lot"（246，21.1%）
6. 滚动到区内地图，停 2 秒

**讲解**
> Clicking a row opens District Evidence. Is the pattern steady, or concentrated in a few months? For 0182, it's steady, around 40 to 80 a month. The last month looks low only because the data ends in mid-September. The top offense is burglary from vehicles, and the top premise is parking lots, so the crew knows what to inspect.

---

## 6. Compare Districts（约 30 秒）

**屏幕操作**
1. 切到 "Compare Districts"
2. 在 "Districts to compare" 里依次点选 0182 和 1494（直接点选项，不按回车）
3. 高亮对比表：Score 87.68 / 87.63，Nighttime 1,167 / 1,097，Recent 147 / 131
4. 滚动到月度对比折线图，停 3 秒

**讲解**
> Compare puts districts side by side. The top two, 0182 and 1494, are almost tied: 87.68 versus 87.63. 0182 has more reports overall and more in the last three months, and both are steady. The app shows the evidence; the manager decides.

---

## 7. 困难案例（约 35 秒）

**屏幕操作**
1. 左侧取消勾选 "All areas"，"Areas" 保持空
2. 高亮侧栏提示 "No areas selected: results are empty…"
3. 高亮 KPI 全部为 0，以及表格位置的蓝色提示 "No districts match the current filters…"
4. 点 "Reset all to defaults"
5. 切到 "District Evidence"，在 "Reporting district" 里点选 "06 · Hollywood · area-level code"
6. 高亮 KPI：25 条，Mapped coverage 0.0%；滚到底部，高亮 "No valid mapped nighttime offenses in this scope."

**讲解**
> Now two edge cases. If I select no areas, the app shows zero and says nothing matches, instead of quietly showing all the data. District 06 has 25 reports but no valid coordinates. They're still counted, but the map shows a message instead of points in the wrong place.

---

## 8. 下载、方法页和局限（约 34 秒）

**屏幕操作**
1. 回到 Priority Overview，高亮并点击 "Worklist CSV"
2. 切到 "Methods and Data Quality"，高亮 "Limitations" 中 "Streetlight asset data is unavailable…" 一条
3. 展开 "Future extension (not part of this MVP)"，停 3 秒

**讲解**
> The Worklist CSV exports this list for the field team. Our biggest limitation: there's no streetlight data yet, so we rank by reported offenses, not lighting conditions. Next, we'd add the city's streetlight map, so the manager can see nearby lights before sending a crew. Thank you.