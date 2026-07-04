# GEE 重跑启动记录

日期：2026-07-04

## 本次实际执行了什么

用户要求“开始跑”。本次按安全顺序尝试启动：

1. GEE 初始化与新湖界 ROI 测试；
2. 新太湖湖界覆盖率单日测试；
3. 为覆盖率脚本增加 `--coverage-output` 参数，避免覆盖旧表；
4. 检查 Google OAuth / Earth Engine 网络连通性；
5. 准备网络恢复后的自动运行脚本。

## 已完成的代码改动

`scripts/10_gee_process_daily.py` 已新增参数：

```text
--coverage-output
```

用途：把新湖界覆盖率写到新的 CSV，例如：

```text
outputs/coverage/daily_valid_coverage_osm_boundary.csv
```

这样不会覆盖旧的：

```text
outputs/coverage/daily_valid_coverage.csv
```

关键脚本已编译通过：

- `scripts/10_gee_process_daily.py`
- `scripts/15_download_modis_daily_v2_fai1240.py`
- `scripts/13_download_hls_tiled.py`

## 实际运行结果

### 1. GEE 初始化测试

尝试通过 Python 初始化 Earth Engine 并读取新湖界 ROI，但进程超过 240 秒未返回，被超时终止。

### 2. 新湖界覆盖率单日测试

命令：

```powershell
py -3.11 scripts\10_gee_process_daily.py --compute-valid-coverage --start 2024-05-14 --end 2024-05-14 --no-resume --coverage-output daily_valid_coverage_osm_boundary_test.csv
```

结果：失败，未进入 GEE 计算阶段。错误发生在 OAuth token 获取阶段。

错误摘要：

```text
HTTPSConnectionPool(host='oauth2.googleapis.com', port=443)
Connection to oauth2.googleapis.com timed out
```

连续 5 次初始化都失败。

### 3. 网络检查

`Test-NetConnection oauth2.googleapis.com -Port 443` 超时。

当前 WinHTTP 代理：

```text
Direct access (no proxy server).
```

环境变量：

```text
HTTP_PROXY=
HTTPS_PROXY=
ALL_PROXY=
NO_PROXY=
```

判断：当前不是脚本算法错误，而是本机到 Google OAuth / Earth Engine 的网络连接不可用或极不稳定。

## 哪些没有跑成

以下任务尚未实际生成结果：

1. `daily_valid_coverage_osm_boundary_test.csv`
2. `daily_valid_coverage_osm_boundary.csv`
3. MODIS v2 `FAI_1240` 单日样本
4. MODIS v2 92 天全量
5. HLS `2024-05-17`
6. HLS `2024-07-31`

## 网络恢复后怎么继续

已经准备脚本：

```text
scripts/run_after_gee_recovers.ps1
```

从 `codex版` 目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_after_gee_recovers.ps1
```

它会依次执行：

1. 新湖界覆盖率 1 天冒烟测试；
2. 新湖界覆盖率 92 天；
3. MODIS v2 `FAI_1240` 单日测试；
4. HLS 剩余两个高覆盖日分块下载；
5. MODIS v2 全量下载；
6. nodata 规范化。

## 当前客观状态

已经开始执行，但 GEE 相关重跑被网络阻断。项目本地脚本已准备好，失败点明确在 `oauth2.googleapis.com` 连接超时，不是 NDVI/FAI、湖界或 QA 算法错误。


## ???????2026-07-04 ????

??????????????????????

1. `Test-NetConnection oauth2.googleapis.com -Port 443`?120 ????
2. `Test-NetConnection earthengine.googleapis.com -Port 443`?120 ????
3. Python ???? `ee.Initialize(project="dulcet-nucleus-498308-g8")`??? 5 ?????? `oauth2.googleapis.com/token` ?????

??????? OAuth token ????????? Earth Engine ??????????????

- `daily_valid_coverage_osm_boundary_test.csv`
- `daily_valid_coverage_osm_boundary.csv`
- MODIS v2 `FAI_1240` GeoTIFF
- HLS `2024-05-17` / `2024-07-31` GeoTIFF

??????????? Google OAuth / Earth Engine ???????????NDVI?FAI ? QA ?????
