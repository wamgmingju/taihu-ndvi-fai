# codex版独立重建说明

创建时间：2026-07-03

本目录按审计后的改进路线独立重建。当前完成的是可复现项目骨架、配置、脚本入口和方法文档。由于本地未确认 Earth Engine 登录状态，也未放入权威太湖 AOI 矢量，当前默认先执行环境检查和 dry-run 覆盖审计。

## 本次实测

- `scripts/00_check_environment.py` 已运行，依赖可识别：`ee`、`numpy`、`pandas`、`rasterio`、`geopandas`、`pyproj`、`shapely`。
- `scripts/01_gee_coverage_audit.py --dry-run` 已运行，生成 `outputs/coverage/daily_sensor_coverage.csv`。
- 已通过 Python `ee.Authenticate()` 完成 Earth Engine 授权，并用项目 `dulcet-nucleus-498308-g8` 成功重新连接。
- 已完成 2024-05-01 至 2024-07-31 的影像数量覆盖审计，结果见 `reports/gee_reconnect_coverage_summary.md`。
- 本地栅格准备、阈值、留一验证、QA 汇总脚本入口已检查；当前因尚未导出新版栅格，正常提示缺少输入数据。

## 和旧版相比的关键改变

1. 高分主线改为 HLS L30/S30，S2/Landsat 作为细查和备份。
2. MODIS Terra/Aqua 分开处理，禁止来源覆盖。
3. Sentinel-3 OLCI 明确为辅助证据，不直接当定量 L2 水色产品。
4. 融合被放到验证之后，不再把插值/重采样称作严格 STARFM。
5. QA 编码重新分层，面积统计必须按 QA 输出。
6. 面积统计使用投影 CRS，不再在经纬度栅格下固定 30 m x 30 m。
