# codex版完整流程自检报告

日期：2026-07-04

## 总体判断

当前项目已经从“只按 bbox/JRC 做初版”推进到“有太湖湖界、MODIS真实观测层、HLS分块下载能力、MODIS插值试验层、文献对比和目录说明”的状态。但必须客观说明：**现有 MODIS/HLS 栅格结果大多是在更换湖界之前生成的，因此不能直接当作最终湖界版成果。**

也就是说，当前最合理的定位是：

- 已完成：方法框架、已有数据自检、目录整理、部分问题修正。
- 部分完成：MODIS 92 天真实观测层、HLS 1 天真实观测层、MODIS 92 天时间插值试验层。
- 未完成：用新太湖湖界重跑覆盖率和栅格；MODIS `FAI_1240` 全量产品；HLS 剩余 2 个高覆盖日；最终跨传感器一致性校正。

## 1. 项目结构自检

### 做了什么

新建并整理了 `codex版` 项目。当前关键目录：

- `configs/`：项目参数、卫星波段、QA配置。
- `data/aoi/`：太湖湖界。
- `scripts/`：20 个 Python 脚本。
- `outputs/coverage/`：覆盖率审计表。
- `outputs/rasters/`：栅格结果。
- `outputs/tables/`：统计表。
- `reports/`：自检、文献、外部数据、问题说明。
- `docs/literature/pdfs/`：两篇本地 PDF 文献副本。

### 相比之前的改动

之前目录里脚本、输出、报告混杂，难以判断哪些是结果、哪些是方法说明。现在新增：

- `PROJECT_STRUCTURE.md`
- `.gitignore`
- `reports/current_questions_action_report.md`
- `reports/full_workflow_self_check_20260704.md`

### 自检结果

本地检查结果：

- `scripts/` 下 20 个 `.py` 脚本全部通过 Python 编译检查。
- `configs/project_config.json`、`configs/sensor_registry.json`、`reports/aoi_boundary_report.json` 都可正常 JSON 读取。
- 本地 Git 已初始化，但尚未提交；`outputs/rasters/` 已被 `.gitignore` 忽略，避免大 GeoTIFF 入库。

### 判断

目录整理是合理的。缺点是历史输出仍保留在原位置，未移动，目的是避免脚本路径失效。后续如果要发布，应只发布脚本、配置、报告和小表格，不把所有 GeoTIFF 放进 Git。

## 2. AOI/湖界自检

### 做了什么

已从 OpenStreetMap Overpass API 获取太湖湖界：

- 文件：`data/aoi/taihu_lake_boundary.geojson`
- OSM relation：`1126533`
- 名称：Taihu Lake
- 面积：`2359.574 km2`

并修改 `scripts/10_gee_process_daily.py`：

- 如果 `data/aoi/taihu_lake_boundary.geojson` 存在，优先使用湖界；
- 如果不存在，才退回 bbox。

### 相比之前的改动

之前流程使用：

- bbox：`[119.8, 30.9, 120.95, 31.55]`
- JRC stable water occurrence >= 75

现在流程会优先使用真正的太湖多边形边界。

### 自检结果

`reports/aoi_boundary_report.json` 显示：

- `area_km2_epsg32651 = 2359.574`
- `ways_total = 73`
- 来源为 Overpass API。

### 判断

这个改动是必要且合理的。2359 km2 与太湖常见面积量级一致，比 bbox 更可信。

但仍有问题：OSM 湖界不是行政权威湖界，也不是 2019 MODIS 文献中“按 Landsat 多年最内湖界目视数字化并向水体腐蚀 250 m”的湖界。下一步应做两件事：

1. 用 OSM 湖界重跑覆盖率和栅格；
2. 对湖界做向水体内缩/腐蚀，减少岸边陆地邻近效应。

## 3. 覆盖率审计自检

### 做了什么

已有覆盖率表：

- `outputs/coverage/daily_valid_coverage.csv`
- 行数：`92`
- 时间：`2024-05-01` 到 `2024-07-31`

### 具体数据

HLS：

- 有 HLS 影像的日期：`77` 天。
- HLS 有效覆盖率 `>= 0.15`：`3` 天。
  - `2024-05-14`：0.557，HLS image count = 6
  - `2024-05-17`：0.160，HLS image count = 17
  - `2024-07-31`：0.179，HLS image count = 15
- HLS 有效覆盖率 `>= 0.05`：`4` 天。

MODIS：

- MODIS 有效覆盖率 `>= 0.15`：`13` 天。
- MODIS 平均有效覆盖率：`0.0606`。

### 相比之前的改动

之前只是说“有多少影像”。现在把“有影像”和“有可用像元”分开了。

### 自检判断

这个表有用，但有一个重大限制：**它是在湖界改动前生成的**，使用的是旧 bbox/JRC 初版逻辑。因此该表只能作为旧版覆盖率参考，不能作为最终湖界版覆盖率。

客观改正建议：

1. 用新 OSM 太湖湖界重跑 `--compute-valid-coverage --no-resume`。
2. 覆盖率输出文件应改名，例如 `daily_valid_coverage_osm_boundary.csv`，不要覆盖旧文件。
3. HLS 阈值建议分两档：
   - `>=0.15`：可做较完整高分观测；
   - `0.05-0.15`：只做局部观测，不做全湖面积判断。

## 4. HLS 高分辨率观测层自检

### 做了什么

已有 HLS 分块下载脚本：

- `scripts/13_download_hls_tiled.py`

已有 HLS 输出：

- `outputs/rasters/hls_observed/Taihu_HLS_observed_NDVI_FAI_QA_20240514.tif`

### 具体数据

`2024-05-14` HLS 文件检查结果：

- 文件大小：`18,813,567 bytes`
- CRS：`EPSG:32651`
- 分辨率：`30 m`
- 波段数：`5`
- shape：`2491 x 3711`
- nodata：`-9999`
- bounds：`(194100.0, 3420300.0, 305430.0, 3495030.0)`
- 有效像元：`1,714,542`
- 有效面积：`1543.0878 km2`

波段统计：

- NDVI：min `-0.9912`，max `0.8916`，mean `-0.3122`
- FAI：min `-7.83e-06`，max `5.91e-05`，mean `-3.54e-06`
- MNDWI：min `-0.6101`，max `0.9968`，mean `0.5197`
- QA：全部为 `10`
- SOURCE：全部为 `10`

### 相比之前的改动

之前 HLS 整幅下载失败，原因是 GEE 直接下载超过 50 MB 限制。现在已经通过 4 x 4 分块方式成功下载并拼接了 `2024-05-14`。

### 自检判断

HLS 分块下载方法是合理的，`2024-05-14` 输出也是真实可读的 30 m GeoTIFF。

但有两个问题：

1. 该 HLS 文件是在新湖界生效前生成的，仍属于旧 AOI 逻辑结果。
2. HLS 的 FAI 数值量级非常小，与 MODIS FAI 不在一个量级，不能直接套 MODIS 或文献阈值。

客观改正建议：

1. 用新湖界重新下载 `2024-05-14`。
2. 继续下载 `2024-05-17`、`2024-07-31`。
3. HLS 暂时只做 NDVI/FAI 指数图，不做最终蓝藻面积。

## 5. MODIS 真实观测层自检

### 做了什么

已有 MODIS 每日真实观测层：

- 目录：`outputs/rasters/modis_daily/`
- 文件数：`92`
- 每个文件 5 个波段：`NDVI, FAI, QA, SOURCE, QUALITY`

### 具体数据

`outputs/tables/modis_daily_raster_summary.csv`：

- 行数：`92`
- 有有效像元日期：`41`
- 0 有效像元日期：`51`
- 总有效像元：`64,655`
- 单日有效像元 min/median/max：`0 / 0 / 8914`

有效像元最多的日期：

1. `2024-07-30`：8914，NDVI mean `-0.2913`，FAI mean `-0.0136`
2. `2024-07-29`：8431，NDVI mean `-0.1245`，FAI mean `0.0128`
3. `2024-05-18`：7072，NDVI mean `-0.3508`，FAI mean `-0.0231`
4. `2024-05-23`：4140，NDVI mean `-0.3615`，FAI mean `-0.0252`
5. `2024-05-08`：3520，NDVI mean `-0.2541`，FAI mean `-0.0107`

`2024-05-14` MODIS 文件检查：

- CRS：`EPSG:32651`
- 分辨率：`500 m`
- 波段数：`5`
- shape：`151 x 223`
- nodata：`-9999`
- 有效像元：`2105`
- 有效面积：`526.25 km2`

### 相比之前的改动

之前只知道 MODIS 下载了 92 天。现在明确知道：

- 92 个文件存在；
- 只有 41 天有有效像元；
- 51 天是空有效观测；
- nodata 已从 `-inf` 修正为 `-9999`。

### 自检判断

MODIS 作为当前主序列是合理的，因为它是唯一覆盖 92 天的日尺度层。

但当前 MODIS 真实观测层不能直接作为最终结果，因为：

1. 51 天无有效像元；
2. 文件是在新湖界前生成的；
3. 当前 FAI 使用 1640 nm，而 2019 太湖 MODIS 文献使用 1240 nm；
4. 没有完成湖界内缩以去除岸边邻近效应。

客观改正建议：

1. 等 GEE 连接恢复，用新湖界重跑 MODIS。
2. 新产品不要覆盖旧产品，输出到 `modis_daily_v2_fai1240/`。
3. 同时输出 `FAI_1640` 和 `FAI_1240`。

## 6. MODIS FAI_1240 改进自检

### 做了什么

已修改 `configs/sensor_registry.json`：

- MODIS Terra/Aqua 新增 `swir1240 = sur_refl_b05`
- 新增波长 `swir1240 = 1240`

已新增脚本：

- `scripts/15_download_modis_daily_v2_fai1240.py`

目标输出：

- `NDVI`
- `FAI_1640`
- `FAI_1240`
- `QA`
- `SOURCE`
- `QUALITY`

### 具体状态

当前检查结果：

- `outputs/rasters/modis_daily_v2_fai1240/` 不存在；
- v2 文件数：`0`。

原因：2026-07-04 运行时 GEE token 初始化连续 5 次连接 `oauth2.googleapis.com` 超时，未下载成功。

### 自检判断

脚本和配置修改是合理的，并且脚本编译通过。但它只是“准备好”，不是“结果已生成”。

客观改正建议：

1. GEE 恢复后先跑 `2024-05-14` 单日样本。
2. 对比旧 `FAI_1640` 和新 `FAI_1240` 的数值分布。
3. 确认后再跑 92 天。

## 7. QA 与缺测自检

### 做了什么

用 `scripts/11_self_check_outputs.py` 检查 MODIS 文件质量，用 `scripts/12_normalize_nodata.py` 修正 nodata。

### 具体数据

当前 `reports/modis_daily_raster_problems.json` 只剩：

- `51` 个 `no_QA_positive_valid_pixels`

之前的 `nodata_is_negative_infinity` 已全部消失。

### 相比之前的改动

之前存在 `nodata=-inf`，现在统一为 `-9999`。

### 自检判断

nodata 修正是客观有效的。

51 天无 QA 有效像元不是格式错误，而是数据质量/掩膜/天气/旧 AOI 下的真实结果。不能把这些天强行说成有真实观测。

客观改正建议：

1. 保留真实观测层的缺测；
2. 插值层单独输出；
3. 不把插值值混进 observed 层。

## 8. MODIS 时间插值层自检

### 做了什么

新增脚本：

- `scripts/16_time_interpolate_modis_daily.py`
- `scripts/17_summarize_gapfilled_status.py`

输出目录：

- `outputs/rasters/modis_daily_gapfilled_linear/`

输出文件数：

- `92`

输出波段：

1. `NDVI`
2. `FAI`
3. `STATUS_30_observed_55_interpolated_90_missing`
4. `NEAREST_OBS_GAP_DAYS`

### 具体数据

总像元状态：

- 真实观测像元：`64,655`
- 线性插值像元：`462,793`
- 仍缺失像元：`2,570,468`

插值最多的日期：

- `2024-07-25`：observed `0`，interpolated `9825`，missing `23848`
- `2024-07-26`：observed `0`，interpolated `9825`，missing `23848`
- `2024-07-27`：observed `0`，interpolated `9825`，missing `23848`
- `2024-07-28`：observed `60`，interpolated `9765`，missing `23848`
- `2024-07-21`：observed `11`，interpolated `9713`，missing `23949`

`2024-05-14` 插值层检查：

- 真实观测：`2105`
- 插值：`4767`
- 缺失：`26801`

### 相比之前的改动

之前只有真实观测层，缺测日期为空。现在新增了 gap-filled 试验层，并明确标记每个像元来源。

### 自检判断

时间插值方法是合理的第一步，因为它简单、可解释，不会伪装成真实观测。

但插值层不能作为最终真实数据。原因：

1. 它基于旧 MODIS 真实观测层；
2. 它只利用时间维度，没有利用 HLS/S2/Landsat 空间细节；
3. 对快速变化蓝藻过程可能过度平滑。

客观改正建议：

1. 用新湖界 MODIS v2 重跑后，再重做插值。
2. 插值层继续保留 `STATUS` 和 `NEAREST_OBS_GAP_DAYS`。
3. 报告中必须把 observed 与 gap-filled 分开。

## 9. 文献流程对比自检

### 做了什么

读取两篇本地 PDF：

1. `land-11-02197-v2.pdf`
2. `remotesensing-11-02269.pdf`

抽取文本到：

- `reports/literature_extracts/`

### 文献给出的关键事实

2019 MODIS + GEE 太湖文献：

- 使用 MODIS 日数据；
- 使用 GEE；
- 使用 FAI；
- 使用湖界/陆地掩膜；
- 岸线向水体方向腐蚀 250 m；
- 云掩膜使用 `Rrc(859 nm) > 0.15`；
- 使用 Rayleigh-corrected reflectance；
- FAI 公式基于 645、859、1240 nm；
- 阈值使用 `FAI > -0.004`。

2022 Landsat + GEE 太湖文献：

- 使用 Landsat 5/7/8 Level-2 surface reflectance；
- 云量筛选 `<20%`；
- 使用 GEE 做云去除、裁剪、合成；
- 使用 FAI 阈值；
- 用 Sentinel-2 同期影像和其他研究结果验证。

### 相比之前的改动

之前只是泛泛说别人用 MODIS/HLS。现在已经从本地 PDF 中确认：

- MODIS 太湖经典流程更偏向 1240 nm；
- 湖界和岸边腐蚀非常重要；
- 高分影像常用于验证，而不是保证每日连续。

### 自检判断

文献支持我们“MODIS 主序列 + HLS/Landsat/S2 高分验证”的方向。

当前最不一致的地方是：我们旧 MODIS 使用 1640 nm FAI，而文献主线使用 1240 nm 和 Rrc。因此必须补 `FAI_1240`，并谨慎对待阈值。

## 10. GitHub/版本控制自检

### 做了什么

已在 `codex版` 初始化本地 Git 仓库，并新增 `.gitignore`。

### 具体状态

当前 `git status` 显示所有项目文件尚未提交，`outputs/rasters/` 和 `scripts/__pycache__/` 被忽略。

### 判断

本地版本控制已准备好，但 GitHub 远程仓库尚未创建。

原因：

- 本机没有 `gh` 命令；
- 环境变量中没有 `GH_TOKEN`、`GITHUB_TOKEN`、`GITHUB_PAT`。

客观改正建议：

1. 你提供一个空 GitHub 仓库 URL；或
2. 安装并登录 GitHub CLI；
3. 然后再提交并推送。

## 11. 当前最大问题清单

按严重程度排序：

1. **现有覆盖率和栅格是旧 AOI 结果**  
   已经改了湖界逻辑，但还没用新湖界重跑主要产品。

2. **MODIS 旧 FAI 与文献不完全一致**  
   旧版使用 1640 nm，文献太湖 MODIS 经典流程使用 1240 nm。

3. **HLS 只有 1 天真正落地**  
   `2024-05-14` 成功，`2024-05-17` 和 `2024-07-31` 未完成。

4. **MODIS 51 天无真实有效观测**  
   插值可以补一部分，但不能替代真实观测。

5. **GEE 连接不稳定**  
   2026-07-04 下载 MODIS v2 时 OAuth token 连续超时。

6. **OSM 湖界不是最终权威湖界**  
   已比 bbox 好，但仍建议替换为官方/论文同款湖界。

## 12. 客观改正计划

### 立即应做

1. GEE 恢复后，用新湖界重跑覆盖率，输出新文件，不覆盖旧文件。
2. 跑 MODIS v2 单日 `2024-05-14`，确认 `FAI_1240` 是否更接近文献。
3. 用新湖界重跑 MODIS v2 92 天。
4. 补 HLS `2024-05-17` 和 `2024-07-31`。

### 然后做

5. 对 OSM 湖界做向水体内缩，测试 250 m 缓冲。
6. 用 MODIS v2 重做时间插值层。
7. 用 HLS 30 m 聚合到 500 m，与 MODIS v2 做同日对比。

### 暂不做

8. 暂不做 FAC/EBA。
9. 暂不做 Chl-a 模型。
10. 暂不把 MODIS 上采样伪装成 30 m 真实图。

## 13. 最终结论

当前项目比之前已经明显更规范：有湖界、有自检、有文献依据、有插值层、有目录说明、有本地 Git。但从科学结果角度看，当前还不是最终版，原因很具体：

- 主结果仍是旧 AOI 生成；
- MODIS 需要补 1240 nm FAI；
- HLS 需要补剩余高覆盖日；
- 插值层只是估算，不能当真实观测；
- 需要用新湖界重跑后再做最终判断。

因此当前最准确的表述是：**codex版已经完成流程重构和初步数据生产，但最终科学产品需要在新湖界 + MODIS FAI_1240 + HLS补齐后重新生成。**
