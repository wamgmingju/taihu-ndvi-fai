# codex版目录说明

本目录是太湖 2024 年 5-7 月每日 NDVI/FAI 产品的独立重建版。当前版本已经把东太湖排除，并以 MODIS v2 每日序列作为主工作产品，HLS 作为高分辨率参考层。

## 入口文件

- `README.md`：项目目标、当前主产品和关键结果。
- `PROJECT_STRUCTURE.md`：目录和文件状态说明。
- `configs/`：项目配置、卫星波段配置、QA 代码说明。
- `scripts/`：可复现脚本，按编号执行。
- `reports/`：每一步检查、问题分析、外部数据和文献对比。
- `docs/`：方法设计、执行计划、文献 PDF。
- `data/aoi/`：研究区边界文件。
- `outputs/`：程序生成结果。

## AOI 文件

- `data/aoi/taihu_lake_boundary.geojson`：完整太湖湖界，来自 OSM relation 1126533，用于追溯和对照。
- `data/aoi/taihu_lake_boundary_no_east_taihu.geojson`：当前最终产品使用的去东太湖湖界。

当前 `configs/project_config.json` 的 `preferred_vector` 已指向：

```text
data/aoi/taihu_lake_boundary_no_east_taihu.geojson
```

面积结果：

- 完整 OSM 太湖湖界：2359.574 km2。
- 剔除东太湖面积：332.384 km2。
- 当前保留湖区：2027.190 km2。

## 关键输出

- `outputs/coverage/daily_valid_coverage_no_east_taihu.csv`：去东太湖后每日 HLS/MODIS 有效水体覆盖率。
- `outputs/rasters/modis_daily_v2_fai1240_no_east_taihu/`：MODIS v2 真实观测层，92 天。
- `outputs/rasters/modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear/`：MODIS v2 线性时间插值每日工作层，92 天。
- `outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/`：最终交付 NDVI 单波段图，92 张。
- `outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/`：最终交付 FAI 单波段图，92 张。
- `outputs/rasters/final_daily_ndvi_fai_no_east_taihu/STATUS/`：最终交付配套状态图，92 张。
- `outputs/rasters/hls_observed_no_east_taihu/`：HLS 30 m 高分真实观测层，当前 3 天。
- `outputs/tables/modis_v2_fai1240_no_east_taihu_raster_summary.csv`：MODIS v2 真观测层每日自检表。
- `outputs/tables/modis_v2_fai1240_no_east_taihu_gapfilled_status_summary.csv`：gap-filled 层每日状态统计。

## 结果状态

- 日期范围：2024-05-01 至 2024-07-31，共 92 天。
- MODIS v2 真观测层：92 个 GeoTIFF；其中 35 天有真实有效像元，57 天无真实有效像元。
- MODIS v2 gap-filled 层：92 个 GeoTIFF，每天 1 个。
- 最终每日两图交付：NDVI 92 张、FAI 92 张。
- HLS 去东太湖观测层：3 个 GeoTIFF，日期为 2024-05-14、2024-05-17、2024-07-31。

## 脚本分类

- `10_gee_process_daily.py`：主 GEE 处理脚本，计算覆盖率并下载 MODIS/HLS。
- `11_self_check_outputs.py`：检查 MODIS GeoTIFF 的投影、波段、有效像元、NDVI/FAI 范围。
- `12_normalize_nodata.py`：把 GeoTIFF 的 nodata 统一成 `-9999`。
- `13_download_hls_tiled.py`：HLS 分块下载并拼接，避免 GEE 单次下载限制。
- `14_fetch_osm_taihu_boundary.py`：从 OSM/Overpass 获取太湖湖界。
- `15_download_modis_daily_v2_fai1240.py`：MODIS v2 日产品，输出 `NDVI`、`FAI_1640`、`FAI_1240`、`QA`、`SOURCE`、`QUALITY`。
- `16_time_interpolate_modis_daily.py`：对 MODIS v2 `NDVI` 和 `FAI_1240` 做逐像元线性时间插值。
- `17_summarize_gapfilled_status.py`：汇总插值层每天观测/插值/缺失像元数。
- `18_exclude_east_taihu_from_aoi.py`：生成去东太湖 AOI。
- `19_compare_hls_modis_consistency.py`：HLS 聚合到 MODIS 网格后做同日一致性检查。
- `20_gis_readiness_and_quicklooks.py`：检查 ArcGIS/QGIS 可读性并生成快速预览图。
- `21_export_daily_ndvi_fai_singleband.py`：把多波段工作层拆成最终 NDVI/FAI 单波段每日图。

## 最容易混淆的一点

`observed` 和 `gapfilled` 必须分开使用：

- `observed`：真实卫星观测，有云、云影或异常反射率就保留缺测。
- `gapfilled`：为了得到每日一张图而生成的估算层，必须结合 `STATUS` 波段解释。

最终每日两图产品是：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/
```

配套状态图在：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/STATUS/
```

但这些图不是“每天每个像元都是真实观测”。真正可靠的表达方式是：每天一张 NDVI、一张 FAI，加上 `STATUS` 说明每个像元来自真实观测、时间插值或仍缺失。
