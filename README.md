# 太湖 2024 年 5-7 月每日 NDVI/FAI 产品（codex版）

本项目的核心目标只有一个：尽可能真实、准确地得到太湖区域 2024-05-01 至 2024-07-31 每日一张 NDVI/FAI 遥感影像图。

当前最终 AOI 已排除东太湖。原因是东太湖水草、浅水、岸线混合像元较多，容易把水草或岸边混合信号误解释为蓝藻/水面漂浮藻信号。

## 当前主产品

最终工作区：

```text
D:\trae work\taihu_ndvi_fai\codex版
```

每日工作产品：

```text
outputs/rasters/modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear/
```

说明：

- 时间范围：2024-05-01 到 2024-07-31，共 92 天。
- 文件数量：92 个 GeoTIFF，每天 1 个。
- 空间分辨率：MODIS 原生 500 m 网格。
- 波段：
  1. `NDVI`
  2. `FAI`，使用 MODIS v2 的 `FAI_1240`
  3. `STATUS`
  4. `NEAREST_OBS_GAP_DAYS`

`STATUS` 不能删，它是判断每个像元可信度的核心：

- `30`：真实 MODIS 观测像元。
- `55`：线性时间插值像元。
- `90`：仍缺失像元。

真实观测层：

```text
outputs/rasters/modis_daily_v2_fai1240_no_east_taihu/
```

高分辨率 HLS 参考层：

```text
outputs/rasters/hls_observed_no_east_taihu/
```

## 当前关键结果

- 去东太湖后保留面积：2027.190 km2。
- MODIS v2 真观测层：92 天文件齐全。
- MODIS v2 有真实有效像元的日期：35 天。
- MODIS v2 无真实有效像元的日期：57 天。
- MODIS v2 真观测有效像元总数：46,867。
- MODIS v2 每日 gap-filled 层：92 天文件齐全。
- gap-filled 总像元状态：
  - 真实观测：46,867
  - 线性插值：341,088
  - 仍缺失：903,633
- HLS 去东太湖高分真观测：3 天，分别是 2024-05-14、2024-05-17、2024-07-31。

## 为什么“有效图”看起来变少

每日图没有变少，仍然是 92 天。变少的是“真实可用像元”。

主要原因：

- 研究区从 bbox/完整太湖边界改成去东太湖湖界，空间对象更严格。
- QA 去除了云、云影、高气溶胶、卷云、临近云、异常反射率等不可靠像元。
- MODIS v2 同时要求红、近红外、1640 nm、1240 nm 都有效，所以比旧版只用 1640 nm 更严格。
- HLS 虽然 2-3 天常有影像过境，但大范围云、云影、拼景覆盖不足和 QA 后有效水体比例低，会让多数日期不能作为高分完整观测。

这不是偏离目标，而是把“真实观测”和“估算补齐”分开，避免把云和缺测硬算成真实 NDVI/FAI。

## 数据来源

- GEE Project ID：`dulcet-nucleus-498308-g8`
- MODIS Terra/Aqua Surface Reflectance：每日粗分辨率主序列。
- HLS L30/S30 v2：30 m 高分辨率参考/校正层。
- JRC Global Surface Water：稳定水体掩膜。
- OSM Taihu lake boundary：太湖湖界基础边界，并生成去东太湖版本。

## 重要报告

- `reports/final_no_east_taihu_product_summary_20260704.md`
- `reports/no_east_taihu_coverage_summary.json`
- `outputs/coverage/daily_valid_coverage_no_east_taihu.csv`
- `outputs/tables/modis_v2_fai1240_no_east_taihu_raster_summary.csv`
- `outputs/tables/modis_v2_fai1240_no_east_taihu_gapfilled_status_summary.csv`

## 主要脚本

- `scripts/18_exclude_east_taihu_from_aoi.py`：生成去东太湖 AOI。
- `scripts/10_gee_process_daily.py`：GEE 覆盖审计和基础下载。
- `scripts/13_download_hls_tiled.py`：HLS 分块下载。
- `scripts/15_download_modis_daily_v2_fai1240.py`：MODIS v2 日产品下载，输出 `FAI_1640` 和 `FAI_1240`。
- `scripts/16_time_interpolate_modis_daily.py`：按像元做线性时间插值，生成每日工作层。
- `scripts/17_summarize_gapfilled_status.py`：汇总每日观测/插值/缺失像元。

## 参考文献

- Hu, C. 2009. Floating Algae Index, Remote Sensing of Environment. https://doi.org/10.1016/j.rse.2009.05.012
- Jia et al. 2019. Taihu cyanobacteria monitoring with MODIS and GEE. https://doi.org/10.3390/rs11192269
- Gao et al. 2006. STARFM. https://doi.org/10.1109/TGRS.2006.872081
- Zhu et al. 2010. ESTARFM. https://doi.org/10.1016/j.rse.2010.05.032
- Zhu et al. 2016. FSDAF. https://doi.org/10.1016/j.rse.2015.11.016
