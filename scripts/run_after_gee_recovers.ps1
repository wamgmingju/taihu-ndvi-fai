$ErrorActionPreference = "Stop"

# Run these from the codex版 project root after Google OAuth / Earth Engine is reachable.

Write-Host "1) Recompute one-day OSM-boundary coverage smoke test"
py -3.11 scripts\10_gee_process_daily.py `
  --compute-valid-coverage `
  --start 2024-05-14 `
  --end 2024-05-14 `
  --no-resume `
  --coverage-output daily_valid_coverage_osm_boundary_test.csv

Write-Host "2) Recompute full OSM-boundary coverage table"
py -3.11 scripts\10_gee_process_daily.py `
  --compute-valid-coverage `
  --no-resume `
  --coverage-output daily_valid_coverage_osm_boundary.csv

Write-Host "2b) Recompute no-East-Taihu coverage table"
py -3.11 scripts\10_gee_process_daily.py `
  --compute-valid-coverage `
  --no-resume `
  --coverage-output daily_valid_coverage_no_east_taihu.csv

Write-Host "3) Download MODIS v2 smoke test with FAI_1240"
py -3.11 scripts\15_download_modis_daily_v2_fai1240.py `
  --start 2024-05-14 `
  --end 2024-05-14 `
  --overwrite

Write-Host "4) Normalize MODIS v2 nodata"
py -3.11 scripts\12_normalize_nodata.py `
  --glob "outputs/rasters/modis_daily_v2_fai1240/*.tif"

Write-Host "5) Download remaining high-coverage HLS dates"
py -3.11 scripts\13_download_hls_tiled.py `
  --start 2024-05-17 `
  --end 2024-05-17 `
  --min-hls-fraction 0.15 `
  --nx 4 `
  --ny 4

py -3.11 scripts\13_download_hls_tiled.py `
  --start 2024-07-31 `
  --end 2024-07-31 `
  --min-hls-fraction 0.15 `
  --nx 4 `
  --ny 4

Write-Host "6) If the smoke test is OK, download full MODIS v2"
py -3.11 scripts\15_download_modis_daily_v2_fai1240.py `
  --overwrite

py -3.11 scripts\12_normalize_nodata.py `
  --glob "outputs/rasters/modis_daily_v2_fai1240/*.tif"

Write-Host "Done"
