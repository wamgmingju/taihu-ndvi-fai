# 太湖 NDVI/FAI 完整流程自检分析

日期：2026-07-05

## 1. 核心目标是否完成

核心目标是得到太湖 2024-05-01 至 2024-07-31 每日 NDVI 和 FAI 图。

当前已经完成“每日两张图”的交付形态：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/
```

数量：

- NDVI：92 张。
- FAI：92 张。
- STATUS：92 张。
- STATUS_uint8_arcgis：92 张。

结论：图已经生成，且可在 GIS 中打开。但这些图不是 92 天全湖全像元真实观测图，而是“真实观测 + 时间插值 + 缺失标记”的每日工作图。

## 2. 数据源和研究区

研究区：

```text
data/aoi/taihu_lake_boundary_no_east_taihu.geojson
```

已剔除东太湖。理由是东太湖水草、浅水、岸线混合像元多，会加大 NDVI/FAI 对蓝藻或漂浮藻解释的误差。

数据源：

- MODIS Terra：`MODIS/061/MOD09GA`
- MODIS Aqua：`MODIS/061/MYD09GA`
- HLS L30：`NASA/HLS/HLSL30/v002`
- HLS S30：`NASA/HLS/HLSS30/v002`
- JRC Global Surface Water：稳定水体掩膜

当前每日主序列是 MODIS Terra/Aqua。HLS 不作为每日主产品，只作为高分辨率参考和同日交叉检查。

## 3. 处理流程自检

### 3.1 AOI

配置文件：

```text
configs/project_config.json
```

当前 `preferred_vector` 指向去东太湖边界。

自检结论：合理。与最初完整太湖边界相比，剔除东太湖可以降低水草和岸线混合误差。

### 3.2 覆盖率审计

文件：

```text
outputs/coverage/daily_valid_coverage_no_east_taihu.csv
```

结果：

- 行数：92。
- HLS 有效水体覆盖率均值：0.0104。
- HLS 有效覆盖率 >= 0.15：2 天。
- HLS 有效覆盖率 >= 0.05：3 天。
- MODIS 有效水体覆盖率均值：0.0627。
- MODIS 有效覆盖率 >= 0.15：14 天。
- MODIS 有效覆盖率 >= 0.05：23 天。

自检结论：HLS 虽然空间分辨率高，但在 2024 年 5-7 月对太湖有效覆盖很少，不能作为每日主序列。MODIS 时间分辨率高，但受云、气溶胶、QA、水体掩膜和反射率有效性限制，真实有效像元仍然少。

### 3.3 MODIS 真实观测层

目录：

```text
outputs/rasters/modis_daily_v2_fai1240_no_east_taihu/
```

结果：

- 文件数：92。
- 有真实有效像元日期：35 天。
- 无真实有效像元日期：57 天。
- 真实有效像元总数：46,867。
- 单日真实有效像元最多：2024-07-30，6,605 个。

处理方法：

- 解码 MODIS `state_1km` 和 `QC_500m`。
- 去除云、云影、高气溶胶、卷云、临近云和低质量像元。
- 使用 JRC 稳定水体掩膜。
- 要求红光、近红外、1240 nm、1640 nm 反射率都有效。
- Terra/Aqua 同日结果通过质量分数择优合成。

自检结论：真实观测层科学上较保守，但代价是有效像元少。57 天不是 MODIS 没有影像，而是 QA 后去东太湖 AOI 内没有留下真实有效像元。

### 3.4 指数计算

NDVI：

```text
NDVI = (NIR - Red) / (NIR + Red)
```

FAI：

- 同时计算 `FAI_1640` 和 `FAI_1240`。
- 最终交付 FAI 使用 MODIS v2 的 `FAI_1240`。

自检结论：`FAI_1240` 更贴近 MODIS FAI 文献常用波段逻辑，但与 HLS FAI 的绝对值不能直接硬比，因为传感器波段和基线不同。

### 3.5 时间插值

目录：

```text
outputs/rasters/modis_daily_v2_fai1240_no_east_taihu_gapfilled_linear/
```

方法：

- 只对同一个像元的时间序列做线性插值。
- 最大插值间隔：前后最近真实观测不超过 10 天。
- 不做空间插值，不用邻近像元硬填空洞。

状态代码：

- `30`：真实 MODIS 观测。
- `55`：线性时间插值。
- `90`：仍缺失。

总状态：

- 真实观测像元：46,867。
- 线性插值像元：341,088。
- 仍缺失像元：903,633。

自检结论：插值是为了形成每日工作图，不是生成新的真实观测。`STATUS=55` 的像元不能当作当天真实卫星观测解释。

### 3.6 最终每日两图导出

目录：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/NDVI/
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/FAI/
```

结果：

- NDVI：92 张，float32，单波段。
- FAI：92 张，float32，单波段。
- 坐标系：EPSG:32651。
- 分辨率：500 m。
- nodata：-9999。

ArcGIS 友好状态图：

```text
outputs/rasters/final_daily_ndvi_fai_no_east_taihu/STATUS_uint8_arcgis/
```

结果：

- 文件数：92。
- dtype：uint8。
- nodata：255。
- 30：真实观测。
- 55：插值。
- 90：缺失。

自检结论：最终交付形态已经符合“每天 NDVI 一张、FAI 一张”的要求。STATUS_uint8_arcgis 比 float32 STATUS 更适合 ArcGIS 唯一值显示。

## 4. 每张图可信度

可信度按每张图中 `STATUS=30` 的真实观测比例判断。

结果：

- A：高可信，真实观测比例 >= 30%，3 天。
- B：中等可信，真实观测比例 10%-30%，8 天。
- C：低可信，真实观测比例 0%-10%，24 天。
- D：无当天真实观测，57 天。

最可信日期：

- 2024-05-18：真实观测 40.7%。
- 2024-07-29：真实观测 41.0%。
- 2024-07-30：真实观测 47.0%。

风险最高日期：

- 57 天没有当天真实观测。如果把这些图当作真实卫星观测图，就是错误解释。
- 这些日期中有一部分像元由时间插值得到，其余为缺失。

自检结论：最终产品必须与 STATUS 一起使用。NDVI/FAI 本身只是数值层，不能单独说明真实性。

## 5. GIS 打开效果自检

检查表：

```text
outputs/tables/gis_readiness_gapfilled_no_east_taihu.csv
```

结果：

- 检查文件：92。
- 元数据异常文件：0。
- 坐标系、分辨率、波段数、nodata 均正常。
- NDVI 全局范围：-0.9961 到 0.9963。
- FAI 全局范围：-0.0730 到 0.2852。

ArcGIS 显示建议：

- NDVI：固定显示范围 `-0.6 到 0.4`。
- FAI：固定显示范围 `-0.05 到 0.05`。
- NoData `-9999` 设透明。
- STATUS_uint8_arcgis 使用唯一值显示。

自检结论：数据文件本身可打开。ArcGIS 中如果出现全 0 或颜色异常，优先检查是否打开了正确文件、是否使用 STATUS_uint8_arcgis、是否错误使用自动拉伸或统计缓存。

## 6. HLS-MODIS 同日交叉检查

文件：

```text
outputs/tables/hls_modis_consistency_no_east_taihu.csv
```

结果：

| 日期 | 配对 MODIS 像元 | NDVI 偏差 MODIS-HLS | NDVI RMSE | NDVI 相关 |
|---|---:|---:|---:|---:|
| 2024-05-14 | 924 | 0.0651 | 0.0750 | 0.7883 |
| 2024-05-17 | 101 | 0.0707 | 0.3531 | 0.4860 |
| 2024-07-31 | 138 | 0.0767 | 0.2910 | 0.8033 |

自检结论：

- 2024-05-14 是最可靠的 HLS-MODIS 校正参考。
- MODIS NDVI 相比 HLS 聚合值有约 0.065-0.077 的系统偏高。
- FAI 空间变化有一定一致性，但 HLS FAI 与 MODIS FAI_1240 不能直接按绝对值相减校正。

## 7. 当前主要问题

1. 真实观测少  
   92 天中只有 35 天有真实有效像元，57 天无当天真实观测。

2. 缺失比例高  
   总缺失像元 903,633，高于真实观测和插值像元。

3. 产品空间分辨率为 500 m  
   不是 30 m 每日真实观测，不能解释出细尺度蓝藻边界。

4. 插值存在“看起来有图”的风险  
   `STATUS=55` 有数值，但不是当天真实卫星观测。

5. NDVI 存在 HLS 对照偏差  
   MODIS NDVI 相比 HLS 聚合结果偏高约 0.07。

6. FAI 未做人工样本阈值校准  
   目前只能说是 FAI 指数图，不能直接给出可靠蓝藻面积结论。

7. ArcGIS 辅助文件不属于产品  
   `.aux.xml` 是 ArcGIS 自动生成的统计/显示缓存，不应作为核心结果提交或解释。

## 8. 客观结论

已经完成：

- 去东太湖 AOI。
- MODIS Terra/Aqua 每日主序列。
- NDVI/FAI 计算。
- QA 过滤。
- 时间插值。
- 92 天 NDVI 单波段图。
- 92 天 FAI 单波段图。
- 92 天 STATUS 图。
- ArcGIS 友好 STATUS_uint8 图。
- GIS 可读性检查。
- HLS-MODIS 同日交叉检查。

没有完成或不能声称完成：

- 没有得到 92 天全湖全像元真实观测。
- 没有得到 30 m 每日真实 NDVI/FAI。
- 没有完成蓝藻阈值人工校准。
- 没有完成成熟多源融合或 STARFM/ESTARFM 类时空融合。

最准确的表述：

```text
本项目生成了 2024 年 5-7 月去东太湖区域的每日 MODIS 500 m NDVI/FAI 工作图，共 92 天。每一天包含 NDVI 和 FAI 两张图，并配套 STATUS 图标记真实观测、时间插值和缺失。产品可用于日序列观察和后续分析，但必须结合 STATUS 使用，不能把插值区域解释为当天真实卫星观测。
```

## 9. 下一步建议

1. 汇报时只把 NDVI/FAI 作为“每日工作图”，不要说成“每日全真实观测图”。
2. 面积统计只对 `STATUS=30` 或明确包含 `STATUS=55` 的估算方案分别统计。
3. ArcGIS 展示时优先使用 `STATUS_uint8_arcgis`。
4. 后续如要做蓝藻面积，应先做人工样本或实测数据阈值校准。
5. 如要提高空间分辨率，应另起一版 HLS/MODIS 融合流程，并先验证 2024-05-14 的 HLS-MODIS 一致性。
