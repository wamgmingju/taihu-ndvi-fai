# codex版方法设计

## 1. 卫星选择

新版采用三层产品，而不是把所有数据硬塞进一个“逐日 30 m 真值图”：

| 层级 | 数据 | 分辨率 | 作用 | 主要限制 |
|---|---|---:|---|---|
| 高分辨率观测层 | HLS L30/S30，补充 S2 SR、L8/L9 L2 | 10-30 m | 水华边界、湖区空间差异、阈值样本、融合验证 | 云、薄云、耀斑和岸线混合仍会造成缺测 |
| 粗分辨率日序列层 | MODIS Terra/Aqua，辅助 Sentinel-3 OLCI | 300-500 m | 判断事件开始、增强、峰值和消退 | 不能解释为真实 30 m 空间细节 |
| 融合估计层 | STARFM/ESTARFM/FSDAF 候选 | 30 m 估计 | 在有验证支持时生成逐日高分估计 | 必须带 QA、误差和留一验证 |

HLS 是主要改进点。它把 Landsat OLI 与 Sentinel-2 MSI 调整到一致 30 m 网格，减少手工跨传感器归一化压力。但 HLS 仍受云和水色大气校正局限影响，所以第一步必须做实际覆盖审计。

## 2. 每个卫星的预处理

### HLS L30/S30

1. 读取 `NASA/HLS/HLSL30/v002` 和 `NASA/HLS/HLSS30/v002`。
2. 使用 `Fmask` 位解码剔除卷云、云、邻近云、云影、雪冰和高气溶胶像元；水体位不能被当作无效像元直接剔除。
3. 将反射率缩放到物理值，保留 source sensor、日期、太阳角、覆盖率。
4. 计算 NDVI、FAI、MNDWI；S30 可额外算红边类指数，但不要和 L30 红边特征混用。
5. 输出高分辨率观测层，QA=10。

### Sentinel-2 SR

1. 使用 `COPERNICUS/S2_SR_HARMONIZED`。
2. 结合 SCL 与 Cloud Score+ 清晰度分数，不只依赖 QA60。
3. 10 m 蓝绿红近红外用于检查边界，20 m SWIR/红边按需要重采样并记录。
4. 主要用于目视样本、关键日期细查和 HLS 验证，不作为唯一主线。

### Landsat 8/9 Collection 2 L2

1. 使用 `LANDSAT/LC08/C02/T1_L2` 和 `LANDSAT/LC09/C02/T1_L2`。
2. 表面反射率缩放为 `DN * 0.0000275 - 0.2`。
3. 用 `QA_PIXEL` 剔除云、云影、雪、卷云、膨胀云，使用 `QA_RADSAT` 剔除饱和。
4. 与 HLS/S2 做近同日清水像元偏差检查。

### MODIS Terra/Aqua

1. 分别读取 `MODIS/061/MOD09GA` 和 `MODIS/061/MYD09GA`。
2. 解码 `state_1km` 和 `QC_500m`，剔除云、云影、卷云、高气溶胶、邻近云和低质量反射率。
3. Terra、Aqua 当日分别计算指数，再生成 `MODIS_TERRA`、`MODIS_AQUA`、`MODIS_TA_BEST` 三套来源；合成层必须携带 `SOURCE` 波段，标明像元来自 Terra 还是 Aqua。
4. 统计时保留 500 m 语义；若重采样到 30 m，只能标记为 QA=30。

### Sentinel-3 OLCI

GEE 的 `COPERNICUS/S3/OLCI` 是 L1 EFR TOA radiance，不是完整水色 L2 产品。codex版只把它作为辅助时间证据。若要定量使用 MCI/NDCI，应补充 OLCI Level-2 水色反射率或叶绿素产品。

## 3. 指数和阈值

FAI 使用 Hu 2009 的红光-近红外-短波红外基线：

`FAI = NIR - (RED + (SWIR - RED) * (lambda_NIR - lambda_RED) / (lambda_SWIR - lambda_RED))`

阈值不再只固定为 0.05。新版至少输出：

- 固定阈值敏感性：0.03、0.05、0.07、0.10。
- 场景内 Otsu 或分位数阈值。
- 若有人工/站点/无人机样本，再训练监督分类模型。

## 4. 面积统计

所有面积统计必须在 `EPSG:32651` 或等面积投影下完成，或逐像元计算真实面积。不能在 WGS84 经纬度网格下固定使用 30 m x 30 m。

## 5. 输出解释

最终结论必须按 QA 分层写：

- 真实高分观测面积。
- 经验证的融合估计面积。
- 粗分辨率日序列趋势。
- 时间插值仅作为连续展示，不进入强结论。
