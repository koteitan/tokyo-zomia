# テスト仕様書

本文書は、ダウンロードアプリ (`download.py`) およびファイル構成変更・gzip圧縮対応の自動テスト項目を定義する。
全テスト項目は Python スクリプトによる自動検証で実施する。

プレビューアプリ (`index.html` / `index.js` / `style.css`) の描画テストはユーザーによるシステムテスト（目視確認）で実施するため、本仕様書の対象外とする。
ファイル存在・構文・参照整合性は自動テストの対象とする。

---

## 1. 対象水系の特定

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-101 | Wikidata SPARQL で相模湾に流入する河川が取得できる | download.py の出力に「相模湾:」と1以上の水系数が含まれる | download.py の標準出力をキャプチャし、正規表現 `相模湾.*\d+水系` にマッチすることを検証 |
| DL-102 | Wikidata SPARQL で東京湾に流入する河川が取得できる | download.py の出力に「東京湾:」と1以上の水系数が含まれる | download.py の標準出力をキャプチャし、正規表現 `東京湾.*\d+水系` にマッチすることを検証 |
| DL-103 | 取得した河川名からW05の水系域コードが正しく照合される | rivers.geojson.gz の全 Feature に空でない suikei_code が存在する | Python で rivers.geojson.gz を gzip 解凍して読み込み、全 Feature の properties["suikei_code"] が空文字でないことを検証 |
| DL-104 | 対象都道府県のデータがダウンロードされる | download.py の出力に対象都道府県(14,13,12,11,19,10,09,08)のダウンロード表示が含まれる | download.py の標準出力をキャプチャし、各都道府県コードに対応する出力が存在することを検証 |

## 2. 標高300m以上フィルタリング

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-201 | フィルタリングにより区間数が減少する | Step 3 の出力で「フィルタ後」の区間数が「フィルタ前」より少ない | download.py の標準出力からフィルタ前後の区間数を抽出し、フィルタ後 < フィルタ前 であることを検証 |
| DL-202 | rivers.geojson に含まれる河川の座標の最大標高が300m以上に達する経路が存在する | 少なくとも1つの Feature で coordinates の第3要素の最大値が 300 以上 | Python で rivers.geojson.gz を gzip 解凍して読み込み、全 Feature の座標から最大標高を算出し、300 以上の Feature が存在することを検証 |

## 3. DEM標高付与

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-301 | 全頂点に標高値が付与される | rivers.geojson の全 coordinates が [lon, lat, elev] の3要素を持つ | Python で rivers.geojson.gz を gzip 解凍して読み込み、全 Feature の全座標が3要素であることを検証 |
| DL-302 | 標高値が妥当な範囲内にある | 標高が 0m 以上 4000m 以下 | Python で rivers.geojson の全座標の第3要素が 0 以上 4000 以下であることを検証 |
| DL-303 | DEM NoData の頂点が補間されている | 標高に null/NaN がない | Python で rivers.geojson の全座標の第3要素に None/NaN がないことを検証 |
| DL-304 | DEM5A タイルの zoom level 14 が使用されている | cache/dem/ 配下のファイル名が 14_ で始まる | Python で cache/dem/ のファイル一覧を取得し、全ファイル名が `14_` で始まることを検証 |

## 4. 海岸線の範囲

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-401 | 海岸線データが取得される | coastline.geojson.gz に1件以上の Feature が存在する | Python で coastline.geojson.gz を gzip 解凍して読み込み、features の長さが 1 以上であることを検証 |
| DL-402 | bbox 範囲内の海岸線のみが抽出される | 全座標が bbox (lon: 139.155-140.870, lat: 34.900-35.745) 内 | Python で coastline.geojson の全座標が bbox 範囲内であることを検証 |
| DL-403 | 島嶼部(伊豆諸島等)が除外される | 緯度34.9未満の座標が含まれない | Python で coastline.geojson の全座標の緯度が 34.9 以上であることを検証 |
| DL-404 | 河口区間に is_river_mouth プロパティが設定される | is_river_mouth が true/false の boolean 型 | Python で coastline.geojson の全 Feature に is_river_mouth が存在し、bool 型であることを検証 |

## 5. 出力 GeoJSON の形式

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-501 | rivers.geojson.gz が有効な GeoJSON FeatureCollection である | gzip 解凍後 JSON パースが成功し、type が "FeatureCollection" | Python で gzip 解凍後 json.load し、type == "FeatureCollection" を検証 |
| DL-502 | rivers.geojson.gz の各 Feature に仕様の properties が存在する | suikei_code, river_code, river_name, section_type, start_node, end_node が存在 | Python で全 Feature の properties に上記キーが含まれることを検証 |
| DL-503 | rivers.geojson.gz の各 Feature の geometry type が LineString | 全 Feature の geometry.type が "LineString" | Python で全 Feature の geometry["type"] == "LineString" を検証 |
| DL-504 | coastline.geojson.gz が有効な GeoJSON FeatureCollection である | gzip 解凍後 JSON パースが成功し、type が "FeatureCollection" | Python で gzip 解凍後 json.load し、type == "FeatureCollection" を検証 |
| DL-505 | coastline.geojson.gz の各 Feature に仕様の properties が存在する | gyosei_code, is_river_mouth が存在 | Python で全 Feature の properties に上記キーが含まれることを検証 |
| DL-506 | coastline.geojson.gz の各 Feature の geometry type が LineString | 全 Feature の geometry.type が "LineString" | Python で全 Feature の geometry["type"] == "LineString" を検証 |
| DL-507 | coastline.geojson.gz の座標が 2D である | 各座標が2要素 [lon, lat] | Python で全座標の要素数が 2 であることを検証 |

## 6. キャッシュ機能

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-601 | キャッシュディレクトリが作成される | cache/w05/, cache/c23/, cache/dem/, cache/wikidata/ が存在する | Python で os.path.isdir() により各ディレクトリの存在を検証 |
| DL-602 | W05 ZIP ファイルがキャッシュされる | cache/w05/ に1個以上のファイルが存在する | Python で cache/w05/ のファイル数が 1 以上であることを検証 |
| DL-603 | C23 ZIP ファイルがキャッシュされる | cache/c23/ に1個以上のファイルが存在する | Python で cache/c23/ のファイル数が 1 以上であることを検証 |
| DL-604 | DEM タイルがキャッシュされる | cache/dem/ に1個以上のファイルが存在する | Python で cache/dem/ のファイル数が 1 以上であることを検証 |
| DL-605 | Wikidata レスポンスがキャッシュされる | cache/wikidata/ に1個以上のファイルが存在する | Python で cache/wikidata/ のファイル数が 1 以上であることを検証 |

## 7. 進捗表示

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-701 | Step 1/6 の進捗が表示される | 出力に「[Step 1/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 1/6]` が含まれることを検証 |
| DL-702 | Step 2/6 の進捗が表示される | 出力に「[Step 2/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 2/6]` が含まれることを検証 |
| DL-703 | Step 3/6 の進捗が表示される | 出力に「[Step 3/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 3/6]` が含まれることを検証 |
| DL-704 | Step 4/6 の進捗が表示される | 出力に「[Step 4/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 4/6]` が含まれることを検証 |
| DL-705 | Step 5/6 の進捗が表示される | 出力に「[Step 5/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 5/6]` が含まれることを検証 |
| DL-706 | Step 6/6 の進捗が表示される | 出力に「[Step 6/6]」が含まれる | download.py の標準出力をキャプチャし、文字列 `[Step 6/6]` が含まれることを検証 |
| DL-707 | 完了メッセージが表示される | 出力に「完了」が含まれる | download.py の標準出力をキャプチャし、文字列 `完了` が含まれることを検証 |

## 8. アクセス頻度制御

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-801 | Wikidata SPARQL へのアクセス間隔が1秒以上 | リクエスト前に1秒以上の sleep/delay がある | download.py のソースコードを grep し、Wikidata リクエスト前後に `time.sleep(1)` 以上の待機があることを確認 |
| DL-802 | 国土数値情報 (W05/C23) へのアクセス間隔が1秒以上 | リクエスト前に1秒以上の sleep/delay がある | download.py のソースコードを grep し、W05/C23 ダウンロード前後に `time.sleep(1)` 以上の待機があることを確認 |
| DL-803 | 国土地理院 DEM5A へのアクセス間隔が10ms以上 | リクエスト前に10ms以上の sleep/delay がある | download.py のソースコードを grep し、DEM リクエスト前後に `time.sleep(0.01)` 以上の待機があることを確認 |

## 9. エラーハンドリング

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| DL-901 | ネットワークエラー時にリトライが実装されている | リトライロジック（3回リトライ、間隔5秒）がコードに存在する | download.py のソースコードを grep し、リトライ処理（retry/loop/except + sleep(5)）が実装されていることを確認 |
| DL-902 | Shapefile の読み込みで cp932 エンコーディングが使用される | rivers.geojson の river_name に日本語が正しく含まれる | Python で rivers.geojson.gz を gzip 解凍して読み込み、少なくとも1つの Feature の river_name が空でなく日本語文字を含むことを検証 |

## 10. ファイル構成変更

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| RS-101 | index.html が存在する | プロジェクトルートに index.html が存在する | Python で os.path.isfile() により検証 |
| RS-102 | index.js が存在する | プロジェクトルートに index.js が存在する | Python で os.path.isfile() により検証 |
| RS-103 | style.css が存在する | プロジェクトルートに style.css が存在する | Python で os.path.isfile() により検証 |
| RS-104 | preview.html が削除されている | プロジェクトルートに preview.html が存在しない | Python で not os.path.exists() により検証 |
| RS-105 | preview.js が削除されている | プロジェクトルートに preview.js が存在しない | Python で not os.path.exists() により検証 |
| ~~RS-106~~ | ~~旧 .geojson ファイルが出力されない~~ | (スキップ: 旧ファイルとの共存は許容) | — |

## 11. gzip 圧縮

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| RS-201 | rivers.geojson.gz が有効な gzip ファイルである | ファイル先頭2バイトが gzip マジックナンバー (0x1f, 0x8b) | Python でバイナリ読み込みし先頭2バイトを検証 |
| RS-202 | coastline.geojson.gz が有効な gzip ファイルである | ファイル先頭2バイトが gzip マジックナンバー (0x1f, 0x8b) | Python でバイナリ読み込みし先頭2バイトを検証 |
| RS-203 | rivers.geojson.gz が gzip.open で解凍できる | gzip.open による読み込みが成功する | Python で gzip.open + json.loads が例外なく完了することを検証 |
| RS-204 | coastline.geojson.gz が gzip.open で解凍できる | gzip.open による読み込みが成功する | Python で gzip.open + json.loads が例外なく完了することを検証 |
| RS-205 | download.py が gzip モジュールを使用する | ソースコードに `import gzip` が含まれる | Python で download.py を読み込み `import gzip` の存在を検証 |
| RS-206 | download.py が gzip.open で書き込む | ソースコードに `gzip.open` が含まれる | Python で download.py を読み込み `gzip.open` の存在を検証 |
| RS-207 | 圧縮によりファイルサイズが削減される | .gz ファイルサイズが解凍後サイズの80%未満 | Python でファイルサイズと解凍後サイズを比較 |

## 12. フロントエンド参照整合性

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| RS-301 | index.html が style.css を参照する | `href="style.css"` が HTML に含まれる | Python で index.html を読み込み文字列検索 |
| RS-302 | index.html が index.js を参照する | `src="index.js"` が HTML に含まれる | Python で index.html を読み込み文字列検索 |
| RS-303 | index.html にインライン `<style>` がない | `<style>` タグが HTML に含まれない | Python で index.html を読み込み文字列検索 |
| RS-304 | index.js が DecompressionStream を使用する | `DecompressionStream` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| RS-305 | index.js が .geojson.gz パスを参照する | `rivers.geojson.gz` と `coastline.geojson.gz` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| RS-306 | index.js が旧 .geojson パスを参照しない | `fetch("data/rivers.geojson")` が JS に含まれない | Python で index.js を読み込み文字列検索 |
| RS-307 | index.html が有効な HTML5 文書である | `<!DOCTYPE html>` で始まり `<html`, `<head>`, `<body>` タグを含む | Python で index.html を読み込み基本構造を検証 |
| RS-308 | style.css が空でない | ファイルサイズが0より大きい | Python で os.path.getsize() > 0 を検証 |
| RS-309 | spec-preview.md が新ファイル名を記載する | `index.html`, `index.js`, `style.css`, `.geojson.gz`, `DecompressionStream` を含む | Python で docs/spec-preview.md を読み込み文字列検索 |
| RS-310 | spec-preview.md が旧ファイル名を記載しない | `preview.html`, `preview.js` を含まない | Python で docs/spec-preview.md を読み込み文字列検索 |

## 13. マウスホバー・ハイライト — GeoJSON properties

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-101 | 全 Feature に start_node プロパティが存在する | rivers.geojson.gz の全 Feature に start_node が存在 | Python で gzip 解凍して全 Feature を検証 |
| HV-102 | 全 Feature に end_node プロパティが存在する | rivers.geojson.gz の全 Feature に end_node が存在 | Python で gzip 解凍して全 Feature を検証 |
| HV-103 | 全 Feature に river_name プロパティが存在する | rivers.geojson.gz の全 Feature に river_name が存在 | Python で gzip 解凍して全 Feature を検証 |
| HV-104 | start_node が空でない Feature が存在する | 1件以上の Feature で start_node が非空 | Python で空でない start_node の件数をカウント |
| HV-105 | end_node が空でない Feature が存在する | 1件以上の Feature で end_node が非空 | Python で空でない end_node の件数をカウント |

## 14. マウスホバー・ハイライト — 隣接グラフ構築

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-201 | start_node/end_node からノード集合が構築できる | ノード数が1以上 | Python で隣接マップを構築しノード数を検証 |
| HV-202 | セグメント数が1以上 | Feature 数が1以上 | Python で Feature 数を検証 |
| HV-203 | 大多数のセグメントが start_node と end_node の両方を持つ | 90%以上のセグメントが両方持つ | Python で両方持つセグメントの割合を検証 |
| HV-204 | 隣接マップの整合性 | nodeToSegs[node] の各セグメントがそのノードを start/end に持つ | Python で全ノードについて整合性を検証 |

## 15. マウスホバー・ハイライト — ノード次数

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-301 | degree==1（源流・河口）のノードが存在する | 1件以上 | Python でノード次数を計算し degree==1 のノード数を検証 |
| HV-302 | degree==2（通過点）のノードが存在する | 1件以上 | Python でノード次数を計算し degree==2 のノード数を検証 |
| HV-303 | degree>=3（分岐・合流）のノードが存在する | 1件以上 | Python でノード次数を計算し degree>=3 のノード数を検証 |
| ~~HV-304~~ | ~~degree 分布が妥当~~ | (スキップ: データ量・ノード統合で変動するため) | — |
| HV-305 | 最大次数が妥当な範囲 | 最大次数 <= 20 | Python で最大次数を検証 |

## 16. マウスホバー・ハイライト — フラッドフィル

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-401 | フラッドフィルが有限集合を返す | 結果セグメント数が1以上かつ全体以下 | Python で仕様通りのフラッドフィルを実装し実行 |
| HV-402 | フラッドフィル結果に開始セグメントが含まれる | 開始インデックスが結果に含まれる | Python で結果集合に開始セグメントが含まれるか検証 |
| HV-403 | degree==2 のノードの先の隣接セグメントが全て含まれる | 境界条件が正しい | Python でフラッドフィル結果の境界を検証 |
| HV-404 | 複数サンプルで一貫して妥当な結果 | 20サンプル全て妥当 | Python でランダム20件のフラッドフィルを検証 |

## 17. マウスホバー・ハイライト — index.js 実装

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-501 | nodeToSegs 隣接マップが構築される | `nodeToSegs` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-502 | nodeDegree 次数が計算される | `nodeDegree` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-503 | floodFillSegments 関数が存在する | `floodFillSegments` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-504 | findNearestSegment 関数が存在する | `findNearestSegment` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-505 | projectToScreen 関数が存在する | `projectToScreen` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-506 | distPointToSegment2D 関数が存在する | `distPointToSegment2D` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-507 | 15px 閾値が設定されている | `< 15` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-508 | degree==2 判定による探索停止 | `!== 2` または `!= 2` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-509 | highlightSet によるハイライト管理 | `highlightSet` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-510 | tooltip 要素の使用 | `tooltip` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-511 | 河川名が空の場合「(名称不明)」を表示 | `(名称不明)` が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-512 | ドラッグ中はホバーをスキップ | `dragging` と `rightDrag` の判定が JS に含まれる | Python で index.js を読み込み文字列検索 |
| HV-513 | mouseleave でハイライト解除 | `mouseleave` が JS に含まれる | Python で index.js を読み込み文字列検索 |

## 18. マウスホバー・ハイライト — 仕様書記載

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| HV-601 | spec-preview.md にホバーセクションが存在 | 「マウスホバー」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |
| HV-602 | spec-preview.md に隣接グラフの記載 | 「隣接」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |
| HV-603 | spec-preview.md にフラッドフィルの記載 | 「フラッドフィル」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |
| HV-604 | spec-preview.md に degree!=2 の停止条件 | 「degree!=2」または「degree==2」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |
| HV-605 | spec-preview.md に 15px 閾値の記載 | 「15px」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |
| HV-606 | spec-preview.md にツールチップの記載 | 「ツールチップ」の記載 | Python で docs/spec-preview.md を読み込み文字列検索 |

## 19. グラフ構造検証 — フィルタリングの完全性

仕様: 「標高300m以上の源流から、指定範囲の河口に繋がるまでの経路に存在するあらゆる河川のポリライン」
全セグメントがノードグラフ上で河口から到達可能であることを構造的に検証する。

### 19-1. グラフ構築

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-101 | start_node/end_node からノード集合を構築 | ノード数 > 0 | Python で隣接マップを構築しノード数を検証 |
| GR-102 | セグメント数が1以上 | Feature 数 > 0 | Python で Feature 数を検証 |

### 19-2. 河口ノードの特定

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-201 | 河口ノード（次数1, bbox内, 標高<10m）が存在する | 河口ノード数 > 0 | Python でノード次数・座標・標高から河口を特定 |
| GR-202 | bbox 内に次数1のノードが存在する | bbox 内の次数1ノード > 0 | Python で bbox 内の次数1ノード数を検証 |

### 19-3. 河口からの到達可能性

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-301 | 全セグメントが河口から BFS で到達可能 | 到達可能セグメント = 全セグメント | Python で河口ノードから BFS し到達可能セグメント数を検証 |
| GR-302 | 到達不能セグメントが存在しない | 到達不能セグメント = 0 | Python で到達不能セグメント数を検証 |
| GR-303 | 到達可能率が100% | 100% | Python で到達可能率を検証 |

### 19-4. 不到達セグメントの診断

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-401 | 不到達セグメントが存在しない | 不到達セグメント = 0、存在する場合は水系・座標範囲を診断出力 | Python で不到達セグメントの属性を集計 |

### 19-5. 源流ノードの検証

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-501 | 源流ノード（次数1, 非河口）が存在する | 源流ノード数 > 0 | Python で次数1かつ非河口のノード数を検証 |
| GR-502 | 標高300m以上の源流ノードが存在する | 300m以上の源流ノード > 0 | Python で源流ノードの標高を検証 |
| GR-503 | 全セグメントが300m以上源流から BFS で到達可能 | 到達可能セグメント = 全セグメント | Python で300m以上源流から BFS し到達可能セグメント数を検証 |

### 19-6. 双方向到達可能性

| テストID | テスト内容 | 期待結果 | 確認方法 |
|----------|-----------|---------|---------|
| GR-601 | 全セグメントが河口・300m源流の両方から到達可能 | 両方から到達可能 = 全セグメント | Python で河口 BFS と源流 BFS の共通集合が全セグメントであることを検証 |

---

## テスト環境

| 項目 | 値 |
|------|-----|
| OS | Linux / WSL2 |
| Python | 3.10+ |
| データ | download.py で生成した data/rivers.geojson.gz, data/coastline.geojson.gz |

## テスト実施手順

1. `download.py` を実行し、標準出力をファイルにキャプチャする
2. ホワイトボックステスト (`test/white/test_restructure.py`) を実行する
3. ブラックボックステスト (`test/blackbox/test_blackbox.py`, `test/blackbox/test_hover.py`, `test/blackbox/test_domain.py`) を実行する
4. 結果を docs/test-report.md に記録する
