# codex版目录说明

## 入口文件

- `README.md`：项目简述。
- `PROJECT_STRUCTURE.md`：当前目录分类说明。
- `configs/`：项目配置、卫星波段配置、QA 代码说明。
- `scripts/`：可复现脚本，按编号执行。
- `reports/`：每一步的检查、问题分析、外部数据和文献对比。
- `docs/`：方法设计、执行计划、文献 PDF。
- `data/aoi/`：研究区边界文件。
- `outputs/`：程序生成结果。

## 关键数据分类

- `data/aoi/taihu_lake_boundary.geojson`：当前使用的太湖湖界，来自 OSM relation 1126533。它比 bbox 更合理，但仍是临时可复现湖界，不等于行政权威湖界。
- `outputs/coverage/daily_valid_coverage.csv`：按日期统计 HLS/MODIS 有效水体覆盖率。
- `outputs/rasters/modis_daily/`：MODIS 真实观测层，500 m，已下载 92 天，但其中 51 天没有 QA 有效像元。
- `outputs/rasters/hls_observed/`：HLS 30 m 真实观测层，目前只有 `2024-05-14` 成功落地。
- `outputs/rasters/modis_daily_gapfilled_linear/`：MODIS 线性时间插值试验层，500 m，92 天。
- `outputs/tables/modis_daily_raster_summary.csv`：MODIS 真实观测层自检表。
- `outputs/tables/modis_gapfilled_status_summary.csv`：插值层每日状态统计。

## 脚本分类

- `10_gee_process_daily.py`：主 GEE 处理脚本，计算覆盖率并下载 MODIS/HLS。
- `11_self_check_outputs.py`：检查 MODIS GeoTIFF 的投影、波段、有效像元、NDVI/FAI范围。
- `12_normalize_nodata.py`：把 GeoTIFF 的无穷 nodata 统一成 `-9999`。
- `13_download_hls_tiled.py`：HLS 分块下载并拼接，避免 GEE 单次 50 MB 下载限制。
- `14_fetch_osm_taihu_boundary.py`：从 OSM/Overpass 获取太湖湖界。
- `14_fetch_hydrolakes_taihu_boundary.py`：尝试从 HydroLAKES/GEE 获取湖界；当前因 GEE连接超时未成功。
- `15_download_modis_daily_v2_fai1240.py`：MODIS v2，计划输出 `FAI_1640` 和 `FAI_1240`，当前因 GEE token 连接超时未跑通。
- `16_time_interpolate_modis_daily.py`：对 MODIS NDVI/FAI 做线性时间插值试验。
- `17_summarize_gapfilled_status.py`：汇总插值层每天观测/插值/缺失像元数。

## 文献和外部数据

- `docs/literature/pdfs/`：两篇本地 PDF 文献副本。
- `reports/literature_extracts/`：PDF 抽取文本。
- `reports/existing_datasets_inventory.md`：别人做好的数据集清单。
- `reports/external_data_reliability_check.md`：本地数据与文献/GitHub做法对比。

## 当前最容易混淆的一点

`observed` 和 `gapfilled` 必须分开：

- observed：真实卫星观测，有云/缺测就保留缺测。
- gapfilled：基于真实观测做时间插值或多源融合，是估算层，必须保留状态标记。
