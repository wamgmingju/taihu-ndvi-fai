// GEE Code Editor quick checks for taihu_ndvi_fai codex版.
// Paste into https://code.earthengine.google.com/ after adjusting AOI.

var taihuBbox = ee.Geometry.Rectangle([119.80, 30.90, 120.95, 31.55]);
var start = '2024-05-01';
var end = '2024-07-31';

var hlsL30 = ee.ImageCollection('NASA/HLS/HLSL30/v002')
  .filterBounds(taihuBbox)
  .filterDate(start, end);

var hlsS30 = ee.ImageCollection('NASA/HLS/HLSS30/v002')
  .filterBounds(taihuBbox)
  .filterDate(start, end);

var modTerra = ee.ImageCollection('MODIS/061/MOD09GA')
  .filterBounds(taihuBbox)
  .filterDate(start, end);

var modAqua = ee.ImageCollection('MODIS/061/MYD09GA')
  .filterBounds(taihuBbox)
  .filterDate(start, end);

print('HLS L30 count', hlsL30.size());
print('HLS S30 count', hlsS30.size());
print('MODIS Terra count', modTerra.size());
print('MODIS Aqua count', modAqua.size());

Map.centerObject(taihuBbox, 9);
Map.addLayer(taihuBbox, {color: 'cyan'}, 'Taihu bbox');
