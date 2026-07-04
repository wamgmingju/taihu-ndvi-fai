# 执行计划

## 第 0 步：环境检查

运行 `scripts/00_check_environment.py`，确认 Python、Earth Engine、rasterio、geopandas、pyproj、numpy、pandas 是否可用。输出 `reports/environment_check.json`。

## 第 1 步：AOI 与网格

放入太湖湖面边界和湖区分区：

- `data/aoi/taihu_lake_boundary.geojson`
- `data/aoi/taihu_subregions.geojson`

没有权威矢量时，只允许 bbox 做 GEE 初筛，正式统计必须等待真实矢量。

## 第 2 步：覆盖审计

运行 `scripts/01_gee_coverage_audit.py`。

它应该输出每一天、每个传感器的：

- 影像数量。
- 清晰水体像元比例。
- 云/云影比例。
- 是否足以作为高分辨率观测日。

这一步决定“有多少天能真实观测”，避免先验承诺 92 天都是 30 m 可信结果。

## 第 3 步：导出高分观测层

运行 `scripts/02_gee_export_hls_observations.py`，导出 HLS L30/S30 的同日高分观测。必要时再用 S2/L8/L9 做补充导出。

输出必须包含：

- NDVI、FAI、MNDWI。
- 原始传感器来源。
- QA。
- 有效覆盖率。

## 第 4 步：导出粗分日序列

运行 `scripts/03_gee_export_modis_daily.py`，分别导出 Terra、Aqua 和 Terra+Aqua best-pixel composite。严禁把 Aqua 命名为 Terra。

运行 `scripts/04_gee_export_s3_olci_aux.py` 时，只把 OLCI 作为辅助证据，除非另有 Level-2 水色产品输入。

## 第 5 步：本地栅格准备

运行 `scripts/05_prepare_rasters.py`：

- 检查 CRS、transform、nodata。
- 投影到分析 CRS。
- 裁剪到太湖湖面。
- 写入统一元数据。

## 第 6 步：指数、阈值和样本

运行 `scripts/06_index_and_threshold.py`，对每个观测日输出 FAI 阈值敏感性表。若没有独立样本，只能报告阈值敏感性，不能声称监督分类精度。

## 第 7 步：融合候选

运行 `scripts/07_fusion_placeholder.py` 查看待接入接口。这个脚本不会伪装成 STARFM；正式融合需接入 STARFM/ESTARFM/FSDAF 实现，并记录高低分影像对、窗口、权重、传感器偏差校正。

## 第 8 步：留一日期验证

运行 `scripts/08_leave_one_out_validation.py`：

- 移除某个真实高分观测日期。
- 用前后高分日期 + 粗分日序列预测该日。
- 与被移除真值比较 RMSE、MAE、IoU、F1、面积误差。

若有效高分日期少于 10 天，报告应写成探索性案例，不宜声称稳健逐日产品。

## 第 9 步：QA 分层面积

运行 `scripts/09_summarize_qa_area.py`，输出按日期、湖区、QA 分层的面积。正式结论只引用可解释的 QA 层。

