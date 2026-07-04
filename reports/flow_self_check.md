# codex版完整流程自检

自检时间：2026-07-03

## 0. 自检范围

检查对象为 `D:\trae work\taihu_ndvi_fai\codex版`。本次检查覆盖配置、卫星数据选择、预处理方法、覆盖审计、导出脚本、本地栅格准备、阈值分析、融合接口、留一验证和 QA 面积统计。

当前结论：新版流程骨架和方法约束已成立，但尚未完成真实 GEE 影像查询和导出。原因是本机 Earth Engine 尚未授权，且太湖湖面边界/湖区分区矢量尚未放入。

## 1. 项目配置检查

做了什么：读取 `configs/project_config.json`、`configs/sensor_registry.json`、`configs/qa_codes.json`。

怎么做：用 Python 检查日期、CRS、传感器数量、QA 编码和 AOI 文件是否存在。

检查结果：

- 时间范围：2024-05-01 至 2024-07-31，共 92 天。
- 分析投影：`EPSG:32651`，用于面积统计。
- 存储 CRS：`EPSG:4326`，只用于数据交换/显示。
- 传感器数量：8 类。
- QA 编码：0、10、11、20、30、40、90。
- AOI 缺口：`data/aoi/taihu_lake_boundary.geojson` 和 `data/aoi/taihu_subregions.geojson` 尚不存在。

判断：配置框架合理；正式面积统计前必须补权威湖面和湖区分区矢量。

## 2. 数据源和用途检查

| 数据 | 用途 | 处理分辨率 | 角色 |
|---|---:|---:|---|
| HLS L30 | 高分主线 | 30 m | Landsat 8/9 harmonized surface reflectance |
| HLS S30 | 高分主线 | 30 m | Sentinel-2 harmonized surface reflectance |
| Sentinel-2 SR | 细节检查 | 10 m | 云少日期的岸线、水华边界、目视样本 |
| Landsat 8/9 L2 | 备份和长期一致性 | 30 m | HLS 不足时补充 |
| MODIS Terra | 粗分日序列 | 500 m | 日尺度趋势 |
| MODIS Aqua | 粗分日序列 | 500 m | 与 Terra 互补 |
| Sentinel-3 OLCI | 辅助水色证据 | 300 m | 只辅助，不直接作为定量 L2 |

判断：卫星选择与改进目标一致。高分层负责空间边界，MODIS/OLCI 负责时间证据，融合层必须另行验证。

## 3. 覆盖审计检查

做了什么：运行 `scripts/01_gee_coverage_audit.py --dry-run`。

怎么做：生成每日 x 传感器矩阵，不下载影像。

检查结果：

- 输出文件：`outputs/coverage/daily_sensor_coverage.csv`
- 行数：736 行，即 92 天 x 8 数据源。
- 当前状态：全部为 `DRY_RUN`。

待完成：GEE 授权后，需要把 `image_count`、`valid_water_fraction`、`cloud_fraction` 从空值变成真实统计。这个步骤应先于任何正式导出。

## 4. 高分辨率观测层检查

脚本：`scripts/02_gee_export_hls_observations.py`

数据：`NASA/HLS/HLSL30/v002`、`NASA/HLS/HLSS30/v002`

处理方法：

1. 对 HLS L30/S30 分别按日筛选。
2. 使用 `Fmask` 位解码剔除卷云、云、邻近云、云影、雪冰、高气溶胶。
3. 保留水体位，不把水体当无效像元剔除。
4. 反射率乘 `0.0001`。
5. 计算 NDVI、FAI、MNDWI。
6. 输出 QA=10，代表同日高分真实观测。
7. 导出到 `EPSG:32651`、30 m。

自检发现并已修正：

- 原代码未处理 HLS 高气溶胶位，已补入 `aerosol_not_high` 掩膜。

仍需注意：

- HLS 是陆地表面反射率产品，不等同专用内陆水色大气校正产品。FAI 可作漂浮藻相对指标；叶绿素定量不能直接靠这一步完成。

## 5. MODIS 日序列检查

脚本：`scripts/03_gee_export_modis_daily.py`

数据：`MODIS/061/MOD09GA`、`MODIS/061/MYD09GA`

处理方法：

1. Terra 与 Aqua 分开读取。
2. 使用 `state_1km` 和 `QC_500m` 解码云、云影、气溶胶、卷云、内部云、邻近云、反射率质量。
3. 反射率乘 `0.0001`。
4. 计算 NDVI、FAI。
5. 分别输出 Terra、Aqua。
6. Terra/Aqua 合成使用 `QUALITY` 波段选较优像元。
7. 输出 `SOURCE` 波段：1=Terra，2=Aqua，避免来源丢失。

自检发现并已修正：

- 原来 `MODIS_TA_BEST` 用 `qualityMosaic("QA")`，但 QA 都是 30，不能真正选最佳像元。已改为 `QUALITY`。
- 原来合成层没有像元来源，已加入 `SOURCE`。

判断：新版已经避免旧流程 Aqua 来源被写成 Terra 的核心问题。

## 6. Sentinel-3 OLCI 检查

脚本：`scripts/04_gee_export_s3_olci_aux.py`

数据：`COPERNICUS/S3/OLCI`

处理方法：

- 仅作为辅助水色证据。
- dry-run 和正式运行都会提示：GEE 中该集合是 L1 EFR TOA radiance，不是定量 L2 水色产品。

判断：这个约束是必要的。若要定量 MCI/NDCI 或叶绿素，应另接 Sentinel-3 OLCI Level-2 水色数据。

## 7. 本地栅格准备检查

脚本：`scripts/05_prepare_rasters.py`

处理方法：

1. 检查 GeoTIFF 的 CRS、分辨率、shape、nodata。
2. 要求目标分析 CRS 为 `EPSG:32651`。
3. 若没有 AOI 矢量，不允许继续裁剪和正式统计。

当前结果：

- `outputs/rasters` 还没有新版导出的 GeoTIFF，脚本正常提示缺少输入。

判断：这里故意设置得保守，防止回到旧流程 bbox 面积统计的问题。

## 8. 指数和阈值检查

脚本：`scripts/06_index_and_threshold.py`

处理方法：

1. 读取导出的 FAI GeoTIFF。
2. 计算 Otsu 自适应阈值。
3. 同时输出固定阈值敏感性：0.03、0.05、0.07、0.10。

当前结果：

- 尚无新版 FAI 栅格，因此脚本提示缺少输入。

判断：方法设计合理，但真实阈值结论必须等 HLS/MODIS 输出和独立样本后再定。

## 9. 融合接口检查

脚本：`scripts/07_fusion_placeholder.py`

处理方法：

- 当前不伪装成 STARFM/ESTARFM/FSDAF。
- 明确列出真正融合所需条件：前后高分清晰日期、同日/近同日粗分证据、统一投影网格、传感器偏差校正。

判断：这是有意保守的设计。正式生成逐日 30 m 估计前，必须接入真实 STARFM/ESTARFM/FSDAF 实现并做留一验证。

## 10. 留一验证检查

脚本：`scripts/08_leave_one_out_validation.py`

处理方法：

1. 输入真实高分 FAI 和预测 FAI。
2. 计算 RMSE、MAE。
3. 按可配置 FAI 阈值计算 IoU 和 F1。

自检发现并已修正：

- 原来二值阈值固定为 0.05；已改为 `--threshold` 参数，默认仍为 0.05。

当前结果：

- 尚无真实预测栅格，脚本提示需要 `--truth` 和 `--prediction`。

## 11. QA 分层面积统计检查

脚本：`scripts/09_summarize_qa_area.py`

处理方法：

1. 读取 QA GeoTIFF。
2. 按 QA=0/10/11/20/30/40/90 分层统计像元数和面积。
3. 面积通过投影坐标下的 `transform.a * transform.e` 计算。

自检发现并已修正：

- 原脚本在 CRS 不等于 `EPSG:32651` 时只警告但仍计算面积。已改成直接报错停止，避免经纬度网格下错误面积。

当前结果：

- 尚无新版 QA 栅格，因此脚本提示缺少输入。

## 12. 当前不能声称已经完成的内容

以下内容还不能声称已经完成：

1. 真实 GEE 影像数量和有效覆盖率。
2. HLS/S2/Landsat/MODIS 的真实导出。
3. 基于新版数据的 FAI 阈值结果。
4. 真实 STARFM/ESTARFM/FSDAF 融合。
5. 留一日期验证误差。
6. QA 分层面积统计。

原因：

- Earth Engine 尚未授权。
- AOI 湖面边界和湖区分区矢量尚未放入。
- 新版栅格尚未导出。

## 13. 下一步执行顺序

1. 运行 Earth Engine 授权：`earthengine authenticate`。
2. 放入太湖湖面边界：`data/aoi/taihu_lake_boundary.geojson`。
3. 放入湖区分区：`data/aoi/taihu_subregions.geojson`。
4. 运行真实覆盖审计：`py -3.11 scripts\01_gee_coverage_audit.py`。
5. 根据覆盖表选择可用日期，再运行 HLS 和 MODIS 导出。
6. 本地准备栅格并计算阈值敏感性。
7. 若高分日期足够，再接入 STARFM/ESTARFM/FSDAF。
8. 做留一验证。
9. 输出 QA 分层面积和最终报告。

