# テスト結果報告書

- 実施日: 2026-03-29
- テスト仕様: docs/test-spec.md
- テスト対象: ファイル構成変更・gzip圧縮対応 + データ品質 + マウスホバー・ハイライト機能
- 出力データ: data/rivers.geojson.gz, data/coastline.geojson.gz
- テストスクリプト:
  - ホワイトボックステスト: test/white/test_restructure.py
  - ブラックボックステスト: test/blackbox/test_blackbox.py, test/blackbox/test_hover.py

## 結果サマリー

### ホワイトボックステスト (test/white/test_restructure.py)

| 結果 | 件数 |
|------|------|
| PASS | 33 |
| FAIL | 0 |
| **合計** | **33** |

### ブラックボックステスト (test/blackbox/test_blackbox.py)

| 結果 | 件数 |
|------|------|
| PASS | 50 |
| FAIL | 0 |
| SKIP | 1 (RS-106) |
| **合計** | **50** |

### ブラックボックステスト — ホバー機能 (test/blackbox/test_hover.py)

| 結果 | 件数 |
|------|------|
| PASS | 37 |
| FAIL | 0 |
| **合計** | **37** |

### 総合

| 結果 | 件数 |
|------|------|
| PASS | 120 |
| FAIL | 0 |
| SKIP | 1 |
| **合計** | **120** |

**全項目合格**

---

## 10. ファイル構成変更

| テストID | 結果 | 詳細 |
|----------|------|------|
| RS-101 | PASS | index.html 存在確認 |
| RS-102 | PASS | index.js 存在確認 |
| RS-103 | PASS | style.css 存在確認 |
| RS-104 | PASS | preview.html 削除確認 |
| RS-105 | PASS | preview.js 削除確認 |
| RS-106 | SKIP | 旧 .geojson との共存は許容 |

## 11. gzip 圧縮

| テストID | 結果 | 詳細 |
|----------|------|------|
| RS-201 | PASS | rivers.geojson.gz: gzip マジックナンバー確認 |
| RS-202 | PASS | coastline.geojson.gz: gzip マジックナンバー確認 |
| RS-203 | PASS | rivers.geojson.gz: gzip 解凍 + JSON パース成功 |
| RS-204 | PASS | coastline.geojson.gz: gzip 解凍 + JSON パース成功 |
| RS-205 | PASS | download.py に `import gzip` あり |
| RS-206 | PASS | download.py に `gzip.open` あり |
| RS-207 | PASS | rivers.geojson.gz: 圧縮率 25.5%, coastline.geojson.gz: 圧縮率 21.2% |

## 12. フロントエンド参照整合性

| テストID | 結果 | 詳細 |
|----------|------|------|
| RS-301 | PASS | index.html に `href="style.css"` あり |
| RS-302 | PASS | index.html に `src="index.js"` あり |
| RS-303 | PASS | index.html にインライン `<style>` なし |
| RS-304 | PASS | index.js に `DecompressionStream` あり |
| RS-305 | PASS | index.js に `rivers.geojson.gz`, `coastline.geojson.gz` パスあり |
| RS-306 | PASS | index.js に旧 `.geojson` パスなし |
| RS-307 | PASS | index.html: `<!DOCTYPE html>` + 基本タグ構造確認 |
| RS-308 | PASS | style.css: 非空 (21行) |
| RS-309 | PASS | spec-preview.md: 新ファイル名 (index.html/js, style.css, .geojson.gz, DecompressionStream) 記載 |
| RS-310 | PASS | spec-preview.md: 旧ファイル名 (preview.html/js) 記載なし |

---

## 1. 対象水系の特定

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-103 | PASS | 全8471 Feature に空でない suikei_code が存在 |

## 2. 標高300m以上フィルタリング

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-202 | PASS | 300m以上到達 Feature: 3285件, 最大標高: 2145.13m |

## 3. DEM標高付与

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-301 | PASS | 全343848頂点が [lon, lat, elev] の3要素 |
| DL-302 | PASS | 全座標の標高が 0m 以上 4000m 以下 |
| DL-303 | PASS | null/NaN 標高: 0件 |
| DL-304 | PASS | 全3792ファイルが zoom level 14 (14_ で始まる) |

## 4. 海岸線の範囲

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-401 | PASS | 1503 features |
| DL-402 | PASS | 全63039座標が bbox 範囲内 (lon: 139.155-140.870, lat: 34.900-35.745) |
| DL-403 | PASS | 緯度34.9未満の座標: 0件 (島嶼部除外済み) |
| DL-404 | PASS | 全1503 Feature の is_river_mouth が bool 型 |

## 5. 出力GeoJSON形式

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-501 | PASS | rivers.geojson.gz: type == "FeatureCollection" |
| DL-502 | PASS | 全 Feature に suikei_code, river_code, river_name, section_type, start_node, end_node が存在 |
| DL-503 | PASS | 全 Feature の geometry.type == "LineString" |
| DL-504 | PASS | coastline.geojson.gz: type == "FeatureCollection" |
| DL-505 | PASS | 全 Feature に gyosei_code, is_river_mouth が存在 |
| DL-506 | PASS | 全 Feature の geometry.type == "LineString" |
| DL-507 | PASS | 全63039座標が 2D ([lon, lat]) |

## 6. キャッシュ機能

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-601 | PASS | cache/w05/, cache/c23/, cache/dem/, cache/wikidata/ 全て存在 |
| DL-602 | PASS | cache/w05/: 16ファイル |
| DL-603 | PASS | cache/c23/: 6ファイル |
| DL-604 | PASS | cache/dem/: 3792ファイル |
| DL-605 | PASS | cache/wikidata/: 2ファイル |

## 8. アクセス頻度制御

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-801 | PASS | query_wikidata_rivers 内に time.sleep(1) あり |
| DL-802 | PASS | download_w05/download_c23 内に time.sleep(1) あり |
| DL-803 | PASS | load_dem_tile 内に time.sleep(0.05) あり |

## 9. エラーハンドリング

| テストID | 結果 | 詳細 |
|----------|------|------|
| DL-901 | PASS | fetch_url: max_retries=3, retry_delay=5 実装確認 |
| DL-902 | PASS | 日本語河川名を含む Feature が存在 (cp932 エンコーディング正常動作) |

---

## 13. マウスホバー・ハイライト — GeoJSON properties

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-101 | PASS | 全8471 Feature に start_node が存在 |
| HV-102 | PASS | 全8471 Feature に end_node が存在 |
| HV-103 | PASS | 全8471 Feature に river_name が存在 |
| HV-104 | PASS | 空でない start_node: 8471/8471 |
| HV-105 | PASS | 空でない end_node: 8471/8471 |

## 14. マウスホバー・ハイライト — 隣接グラフ構築

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-201 | PASS | ノード数: 7704 |
| HV-202 | PASS | セグメント数: 8471 |
| HV-203 | PASS | start_node と end_node 両方あるセグメント: 8471/8471 (100%) |
| HV-204 | PASS | 隣接マップの整合性: 全ノード↔セグメント対応が正しい |

## 15. マウスホバー・ハイライト — ノード次数

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-301 | PASS | degree==1（端点）: 1982ノード |
| HV-302 | PASS | degree==2（通過点）: 2326ノード |
| HV-303 | PASS | degree>=3（分岐・合流）: 3396ノード |
| HV-304 | PASS | degree 分布が妥当 (1982 < 2326) |
| HV-305 | PASS | 最大次数: 5 |

## 16. マウスホバー・ハイライト — フラッドフィル

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-401 | PASS | フラッドフィルが有限集合を返す（セグメント0から: 2件） |
| HV-402 | PASS | フラッドフィル結果に開始セグメントが含まれる |
| HV-403 | PASS | boundary: degree==2 のノードの先は全て結果に含まれる |
| HV-404 | PASS | 20サンプルのフラッドフィルが全て妥当 |

## 17. マウスホバー・ハイライト — index.js 実装

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-501 | PASS | nodeToSegs 隣接マップ構築コード確認 |
| HV-502 | PASS | nodeDegree 次数計算コード確認 |
| HV-503 | PASS | floodFillSegments 関数確認 |
| HV-504 | PASS | findNearestSegment 関数確認 |
| HV-505 | PASS | projectToScreen 関数確認 |
| HV-506 | PASS | distPointToSegment2D 関数確認 |
| HV-507 | PASS | 15px 閾値設定確認 |
| HV-508 | PASS | degree==2 判定による探索停止確認 |
| HV-509 | PASS | highlightSet によるハイライト管理確認 |
| HV-510 | PASS | tooltip 要素の使用確認 |
| HV-511 | PASS | 「(名称不明)」フォールバック表示確認 |
| HV-512 | PASS | ドラッグ中はホバーをスキップ確認 |
| HV-513 | PASS | mouseleave でハイライト解除確認 |

## 18. マウスホバー・ハイライト — 仕様書記載

| テストID | 結果 | 詳細 |
|----------|------|------|
| HV-601 | PASS | spec-preview.md にホバーセクション記載あり |
| HV-602 | PASS | spec-preview.md に隣接グラフ記載あり |
| HV-603 | PASS | spec-preview.md にフラッドフィル記載あり |
| HV-604 | PASS | spec-preview.md に degree!=2 停止条件記載あり |
| HV-605 | PASS | spec-preview.md に 15px 閾値記載あり |
| HV-606 | PASS | spec-preview.md にツールチップ記載あり |
