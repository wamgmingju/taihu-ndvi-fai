# 已有公开数据集清单：太湖蓝藻/水质/湖泊遥感

检索日期：2026-07-04

## 1. 最推荐：THQBCA 太湖蓝藻综合时间序列数据集

- 名称：A comprehensive time-series dataset linked to cyanobacterial blooms in Lake Taihu
- 数据仓库：https://zenodo.org/records/13917285
- DOI：10.5281/zenodo.13917285
- 论文：https://www.nature.com/articles/s41597-024-04224-w
- 数据量：Zenodo 页面显示 `THQBCA-V2.rar`，约 924.7 MB。
- 内容：26 个变量，分为水质、生物光学、气候、人类活动四类。
- 时间：多变量超过 15 年，其中部分变量约 20 年或 35 年。
- 格式：水质/气候为 xlsx；生物光学和人类活动为 GeoTIFF。
- 遥感相关变量：FAC、Chla、SDD、TSI、水生植被、土地覆盖、人口密度、夜间灯光。
- 分辨率：卫星派生数据 30 m 到 500 m。
- 对本项目的作用：最适合作为太湖背景资料和年度尺度验证数据，尤其可用于对比我们生成的 MODIS/HLS 指数结果是否在合理范围内。
- 局限：其遥感生物光学产品主要提供年度均值；论文明确说明该数据集不能直接支持短期预警，高频每日数据需要联系作者或按文献方法自行生成。

## 2. 太湖/GEE MODIS 蓝藻长期监测流程

- 论文：Long-Term Spatial and Temporal Monitoring of Cyanobacteria Blooms Using MODIS on Google Earth Engine: A Case Study in Taihu Lake
- 链接：https://www.mdpi.com/2072-4292/11/19/2269
- DOI：10.3390/rs11192269
- 数据/代码：论文页面有 GEE 脚本链接和补充材料。
- 数据源：MODIS，GEE 自动流程，2000-2018。
- 变量：蓝藻水华空间分布、月/年尺度统计。
- 对本项目的作用：最适合对比处理流程和季节规律；不是一个完整下载式每日 GeoTIFF 数据集，但可以复现其 GEE 方法。
- 局限：研究期到 2018，不覆盖我们当前 2024 年；需要自己运行脚本或重建流程。

## 3. 中国湖泊 40 年 Landsat 营养状态指数数据集 CNLTSI

- 名称：A dataset of trophic state index for nation-scale lakes in China
- 数据仓库：https://zenodo.org/records/11209734
- DOI：10.5281/zenodo.11209734
- 论文：https://www.nature.com/articles/s41597-024-03506-7
- 数据量：约 515.2 MB。
- 内容：2693 个中国湖泊，1984-2023，Landsat 30 m。
- 变量：annual_TSI、annual_pixel、average_TSI、lake_info。
- 对本项目的作用：可用于对照太湖长期富营养化背景、湖泊边界/湖泊编号、年度趋势；也可参考其水体分类、FAI、TWI、NDWI 规则。
- 局限：这是年度 TSI，不是每日蓝藻图；不能直接验证某一天的 NDVI/FAI。

## 4. 中国典型湖泊卫星-地面同步实测水质数据集

- 名称：Satellite-ground synchronous in-situ dataset of water optical parameters and surface temperature for typical lakes in China
- 数据仓库：https://zenodo.org/records/10989821
- 论文：https://www.nature.com/articles/s41597-024-03704-3
- 代码：https://github.com/VolunteeredGI/Lake-in-situ-dataset-code
- 内容：586 个质控后的同步样点，覆盖 18 个中国典型湖泊。
- 变量：Rrs、Chl-a、TSM、SDD、水表温度等。
- 对本项目的作用：适合校验水质遥感模型、Chl-a/TSM/SDD 反演方法；若里面含太湖样点，可作为实测约束。
- 局限：不是专门的太湖蓝藻时空栅格数据集，也不是每日序列。

## 5. 全球湖泊藻华数据集

- 名称：Global lake algal bloom dataset
- 数据仓库：https://figshare.com/articles/dataset/Global_lake_algal_blooms_datasets_with_a_paper_published_in_Nature_Geoscience_titled_Global_mapping_reveals_increase_in_lacustrine_algal_blooms_over_the_past_decade_https_www_nature_com_articles_s41561-021-00887-x/19401236
- DOI：10.6084/m9.figshare.19401236
- 内容：21878 个淡水湖，Landsat 1982-2019。
- 变量：最大水华范围 MBE、平均水华发生率 BO。
- 对本项目的作用：可查太湖在全球湖泊中的长期水华强度量级，适合宏观对比。
- 局限：统计型数据，不是逐日影像；时间分段较粗。

## 6. NASA/EPA CyAN 数据集

- 项目页：https://www.earthdata.nasa.gov/data/projects/cyan
- 数据：MERIS 2002-2012、Sentinel-3 OLCI 2016 至今。
- 产品：CI_cyano，每日和 7 日最大值合成，300 m。
- 对本项目的作用：算法和产品组织方式很值得参考，尤其是 CI、质量标记、7 日合成、数据发布格式。
- 局限：主要覆盖美国 CONUS 和 Alaska，不覆盖太湖；不能直接作为太湖验证数据。

## 7. 结论

当前能直接用来对比太湖的现成数据集中，优先级如下：

1. THQBCA：最重要，太湖专用，有 FAC/Chla/SDD/TSI/气象/水质，但偏年度尺度。
2. Jia et al. 2019 GEE MODIS 流程：最接近我们的 MODIS 每日处理逻辑，可对比方法和长期规律。
3. CNLTSI：中国湖泊 30 m 年度 TSI，可用于太湖富营养化背景和方法参考。
4. 中国湖泊同步实测数据：可用于水质反演模型校验，需检查是否含足够太湖样点。
5. 全球湖泊藻华数据：宏观背景对照，不适合逐日验证。

没有找到一个公开、可直接下载、覆盖 `2024-05-01` 到 `2024-07-31`、逐日、30 m 或 500 m 的太湖 NDVI/FAI/FAC 成品数据集。因此本项目仍需要自己从 GEE 生成 2024 年日尺度结果，但可以用上述数据集做外部合理性校验。
