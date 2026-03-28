# テスト結果報告書

- 実施日: 2026-03-29
- テスト仕様: docs/test-spec.md
- テスト対象: download.py (実行ログ: logs/download.log)
- 出力データ: data/rivers.geojson, data/coastline.geojson

## 結果サマリー

| 結果 | 件数 |
|------|------|
| PASS | 30 |
| FAIL | 0 |
| **合計** | **30** |

**全項目合格**

---

## 1. 対象水系の特定

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-101 | PASS | 「相模湾: 15水系」を確認 |
| DL-102 | PASS | 「東京湾: 33水系」を確認 |
| DL-103 | PASS | 全8471 Featureに空でないsuikei_codeが存在 |
| DL-104 | PASS | 全8県(14,13,12,11,19,10,09,08)のダウンロード表示を確認 |

## 2. 標高300m以上フィルタリング

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-201 | PASS | フィルタ前: 27189区間 → フィルタ後: 8471区間 |
| DL-202 | PASS | 300m以上到達Feature: 3285件, 最大標高: 2145.1m |

## 3. DEM標高付与

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-301 | PASS | 全343848頂点が[lon, lat, elev]の3要素 |
| DL-302 | PASS | 全座標の標高が0m以上4000m以下 |
| DL-303 | PASS | null/NaN標高: 0件 |
| DL-304 | PASS | 全3792ファイルがzoom level 14 (14_で始まる) |

## 4. 海岸線の範囲

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-401 | PASS | 1503 features |
| DL-402 | PASS | 全63039座標がbbox範囲内 (lon: 139.155-140.870, lat: 34.900-35.745) |
| DL-403 | PASS | 緯度34.9未満の座標: 0件 (島嶼部除外済み) |
| DL-404 | PASS | 全1503 Featureのis_river_mouthがbool型 |

## 5. 出力GeoJSON形式

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-501 | PASS | rivers.geojson: type == "FeatureCollection" |
| DL-502 | PASS | 全Featureにsuikei_code, river_code, river_name, section_type, start_node, end_nodeが存在 |
| DL-503 | PASS | 全Featureのgeometry.type == "LineString" |
| DL-504 | PASS | coastline.geojson: type == "FeatureCollection" |
| DL-505 | PASS | 全Featureにgyosei_code, is_river_mouthが存在 |
| DL-506 | PASS | 全Featureのgeometry.type == "LineString" |
| DL-507 | PASS | 全63039座標が2D ([lon, lat]) |

## 6. キャッシュ機能

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-601 | PASS | cache/w05/, cache/c23/, cache/dem/, cache/wikidata/ 全て存在 |
| DL-602 | PASS | cache/w05/: 16ファイル |
| DL-603 | PASS | cache/c23/: 6ファイル |
| DL-604 | PASS | cache/dem/: 3792ファイル |
| DL-605 | PASS | cache/wikidata/: 2ファイル |

## 7. 進捗表示

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-701 | PASS | [Step 1/6] 確認 |
| DL-702 | PASS | [Step 2/6] 確認 |
| DL-703 | PASS | [Step 3/6] 確認 |
| DL-704 | PASS | [Step 4/6] 確認 |
| DL-705 | PASS | [Step 5/6] 確認 |
| DL-706 | PASS | [Step 6/6] 確認 |
| DL-707 | PASS | 「完了」メッセージ確認 |

## 8. アクセス頻度制御

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-801 | PASS | query_wikidata_rivers内にtime.sleep(1)あり (L199) |
| DL-802 | PASS | download_w05内にtime.sleep(1)あり (L236), download_c23内にtime.sleep(1)あり (L541) |
| DL-803 | PASS | load_dem_tile内にtime.sleep(0.05)あり (L128) |

## 9. エラーハンドリング

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-901 | PASS | fetch_url: max_retries=3, retry_delay=5 実装確認 (L62-76) |
| DL-902 | PASS | 日本語河川名を含むFeatureが存在 (cp932エンコーディング正常動作) |
