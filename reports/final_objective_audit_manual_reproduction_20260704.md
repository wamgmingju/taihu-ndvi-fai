# 最终目标审查与人工复现步骤

日期：2026-07-04

## 1. 最初版本与当前版本有什么不一样

最初版本的问题：

- 输出目录混乱，NDVI、FAI、QA 和中间文件难以区分。
- 研究区边界不够稳定，存在 bbox 或完整太湖边界混用问题。
- 东太湖没有明确排除，容易引入水草、岸线、浅水混合像元误差。
- 每日产品和真实观测产品没有清楚分开，容易把插值/缺测误当成真实卫星观测。
- MODIS 旧版只使用单一 FAI 思路，没有同时输出 `FAI_1240` 和 `FAI_1640` 作敏感性判断。
- 没有完整的 92 天覆盖率审计、状态统计、HLS-MODIS 同日一致性检查。

当前版本的改进：

- 新建 `codex版` 独立目录，按 `configs/`、`scripts/`、`outputs/`、`reports/` 分类。
- 生成并使用去东太湖 AOI：`data/aoi/taihu_lake_boundary_no_east_taihu.geojson`。
- 使用 MODIS Terra/Aqua 作为每日主序列。
- 使用 HLS L30/S30 作为高分辨率参考，不强行把 HLS 当作每日主序列。
- MODIS v2 同时计算 `FAI_1640` 和 `FAI_1240`，最终每日 FAI 使用更贴近 MODIS 文献传统的 `FAI_1240`。
- 生成 92 天多波段工作层，并进一步拆分为最终每日两图：NDVI 92 张、FAI 92 张。
- 保留 `STATUS`，明确每个像元是真实观测、插值还是缺失。
- 运行 GIS 可读性检查和 HLS-MODIS 同日一致性检查。

## 2. 是否完成核心任务

如果任务定义为“2024 年 5-7 月每天两张可在 GIS 打开的 NDVI/FAI 图”，已经完成。

最终目录：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/
```

数量：

- NDVI：92 张。
- FAI：92 张。
- STATUS：92 张。

如果任务定义为“92 天每个像元都必须是真实卫星观测、且达到 30 m 高精度”，没有完成，也不应该声称完成。原因是 2024 年 5-7 月 HLS 高分有效覆盖不足，MODIS 原生分辨率为 500 m，时间插值不是新的真实观测。

## 3. 得到的东西是什么

最终交付：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/Taihu_NDVI_no_east_taihu_YYYYMMDD.tif
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/Taihu_FAI_no_east_taihu_YYYYMMDD.tif
```

配套状态：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/STATUS/Taihu_STATUS_no_east_taihu_YYYYMMDD.tif
```

`STATUS` 代码：

- `30`：真实 MODIS 观测。
- `55`：线性时间插值。
- `90`：仍缺失。

当前总状态：

- 真实观测像元：46,867。
- 线性插值像元：341,088。
- 仍缺失像元：903,633。

## 4. ArcGIS/QGIS 打开检查

脚本：

```text
scripts/20_gis_readiness_and_quicklooks.py
```

检查结果：

- 多波段每日工作层：92 个文件全部可读。
- 最终单波段 NDVI：92 张，GIS 元数据异常数 0。
- 最终单波段 FAI：92 张，GIS 元数据异常数 0。
- 最终 STATUS：92 张，GIS 元数据异常数 0。
- 坐标系：EPSG:32651。
- 分辨率：500 m。
- nodata：-9999。
- NDVI 全局范围：-0.9961 到 0.9963。
- FAI 全局范围：-0.0730 到 0.2852。

预览图：

```text
outputs/quicklooks/gapfilled_no_east_taihu/
```

发现：

- ArcGIS/QGIS 可以打开。
- 如果只看 NDVI/FAI 会产生误解，因为插值像元和真实观测像元看起来都是数值。
- 必须同时看 `STATUS`；例如 `2024-07-25` 没有真实观测像元，主要是插值；`2024-07-30` 真实观测最多；`2024-07-31` 缺失最多。

## 5. 有没有异常或虚假部分

有潜在“虚假感”，但我们已经用 `STATUS` 标出来了。

不能说虚假的部分：

- `STATUS=30` 的像元来自真实 MODIS QA 后观测。

必须谨慎解释的部分：

- `STATUS=55` 是时间插值，不是当天真实卫星观测。
- `STATUS=90` 是缺失，不应参与面积统计或阈值判断。

不能这么说：

```text
我们得到了 92 天全湖全像元真实观测 NDVI/FAI。
```

应该这么说：

```text
我们得到了 92 天每日 NDVI/FAI 工作图，其中每个像元用 STATUS 标明真实观测、插值或缺失。
```

## 6. 和别人做法相比

Jia et al. 2019 在太湖案例中使用 MODIS 和 Google Earth Engine 做长期蓝藻时空监测，说明 MODIS/GEE 是太湖长期、逐日或高时间频率监测的常见路线。Hu 2009 提出的 FAI 是漂浮藻类监测的基础指数方法。HLS 官方资料说明 HLS 是 30 m、2-3 天重访的 Landsat/Sentinel-2 调和产品，但它并不保证每个研究区每天都有有效无云观测。

我们的相同点：

- 使用 MODIS 作为高时间频率主数据。
- 使用 FAI/NDVI 这类光谱指数。
- 使用 GEE 做影像筛选、QA 和批量处理。

我们的不同点：

- 排除了东太湖，降低水草和岸线混合像元影响。
- 把真实观测层和 gap-filled 层分开。
- 每日最终图保留 `STATUS`，不把插值伪装成真实观测。
- 对 HLS 与 MODIS 做同日一致性检查。

可能低于别人或文献正式产品的地方：

- 尚未做实测样本校准。
- 尚未建立 FAI 阈值的本地人工样本验证。
- 尚未做成熟的 STARFM/ESTARFM/FSDAF 融合。
- 目前产品是 500 m 日序列，不是 30 m 真实每日观测。

## 7. HLS-MODIS 一致性检查

脚本：

```text
scripts/19_compare_hls_modis_consistency.py
```

结果：

- `2024-05-14`：配对 MODIS 像元 924，NDVI 相关 0.7883，RMSE 0.0750，是最可靠校正参考。
- `2024-05-17`：配对像元 101，NDVI RMSE 0.3531，不适合单独强校正。
- `2024-07-31`：配对像元 138，HLS 覆盖低，只能辅助。
- MODIS NDVI 比 HLS 聚合值偏高约 0.065-0.077。
- FAI 的空间相关有一定一致性，但 HLS FAI 与 MODIS `FAI_1240` 绝对值不能直接硬比。

## 8. 如果按照流程再做，能不能做出来

可以。当前流程已经脚本化。

复现前提：

- 能访问 GEE。
- GEE Project ID：`dulcet-nucleus-498308-g8`。
- 网络代理可用时设置：

```powershell
$env:HTTP_PROXY='http://127.0.0.1:7897'
$env:HTTPS_PROXY='http://127.0.0.1:7897'
```

人工完整复现步骤：

```powershell
cd "D:\trae work\taihu_ndvi_fai\codex版"

# 1. 确认配置和 AOI
Get-Content configs\project_config.json

# 2. 生成/确认去东太湖 AOI
py -3.11 scripts\18_exclude_east_taihu_from_aoi.py

# 3. 计算去东太湖每日覆盖率
py -3.11 scripts\10_gee_process_daily.py --compute-valid-coverage --no-resume --coverage-output daily_valid_coverage_no_east_taihu.csv

# 4. 下载 MODIS v2 每日真实观测层
py -3.11 scripts\15_download_modis_daily_v2_fai1240.py --output-dir modis_daily_v2_fai1240_no_east_taihu --overwrite

# 5. 下载 HLS 高分参考层
py -3.11 scripts\13_download_hls_tiled.py --start 2024-05-14 --end 2024-05-14 --min-hls-fraction 0.15 --nx 4 --ny 4 --overwrite --output-dir hls_observed_no_east_taihu --tile-dir hls_tiles_no_east_taihu
py -3.11 scripts\13_download_hls_tiled.py --start 2024-05-17 --end 2024-05-17 --min-hls-fraction 0.15 --nx 4 --ny 4 --overwrite --output-dir hls_observed_no_east_taihu --tile-dir hls_tiles_no_east_taihu
py -3.11 scripts\13_download_hls_tiled.py --start 2024-07-31 --end 2024-07-31 --min-hls-fraction 0.05 --nx 4 --ny 4 --overwrite --output-dir hls_observed_no_east_taihu --tile-dir hls_tiles_no_east_taihu

# 6. 对 MODIS v2 做时间插值，得到每日工作层
py -3.11 scripts\16_time_interpolate_modis_daily.py --input-dir modis_daily_v2_fai1240_no_east_taihu --output-dir modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear --max-gap-days 10 --overwrite

# 7. 汇总 STATUS
py -3.11 scripts\17_summarize_gapfilled_status.py --input-dir modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear --output modis_v2_fai1240_no_east_taihu_gapfilled_status_summary.csv

# 8. 做 HLS-MODIS 一致性检查
py -3.11 scripts\19_compare_hls_modis_consistency.py

# 9. 检查 GIS 可读性并生成预览图
py -3.11 scripts\20_gis_readiness_and_quicklooks.py

# 10. 导出最终每日两图
py -3.11 scripts\21_export_daily_ndvi_fai_singleband.py
```

## 9. 人工对照检查步骤

在 ArcGIS/QGIS 中：

1. 打开 `final_daily_ndvi_fai_no_east_taihu/NDVI/Taihu_NDVI_no_east_taihu_20240730.tif`。
2. 打开 `final_daily_ndvi_fai_no_east_taihu/FAI/Taihu_FAI_no_east_taihu_20240730.tif`。
3. 同时打开 `final_daily_ndvi_fai_no_east_taihu/STATUS/Taihu_STATUS_no_east_taihu_20240730.tif`。
4. 检查三者是否位置完全重合。
5. 对 `STATUS=30` 的区域，认为是当天真实 MODIS 观测。
6. 对 `STATUS=55` 的区域，标记为插值，不用于“真实当天面积”统计。
7. 对 `STATUS=90` 的区域，标记为缺失。
8. 换 `2024-07-25` 检查，会看到主要是插值，不应当当作真实观测日。
9. 换 `2024-07-31` 检查，会看到缺失很多，不应当强行补全解释。

## 10. 当前最客观的结论

我们完成了每日 NDVI/FAI 图的交付形态：92 天，每天 NDVI 一张、FAI 一张。

但科学解释必须保守：

- 这是 MODIS 500 m 日产品，不是 30 m 每日真实观测。
- 其中部分像元是线性时间插值，不能称为真实观测。
- 东太湖已排除，这是合理改进。
- 与 HLS 对比显示 NDVI 可能有约 0.07 的系统偏高，需要后续校正或在报告中注明。
- FAI 需要阈值校准，不能只靠图像颜色判断蓝藻面积。

参考：

- Jia et al. 2019, Remote Sensing, Taihu MODIS/GEE cyanobacteria monitoring: https://doi.org/10.3390/rs11192269
- Hu 2009, Floating Algae Index: https://doi.org/10.1016/j.rse.2009.05.012
- MODIS Terra MOD09GA GEE catalog: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD09GA
- MODIS Aqua MYD09GA GEE catalog: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MYD09GA
- HLS L30 GEE catalog: https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSL30_v002
- HLS S30 GEE catalog: https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSS30_v002
