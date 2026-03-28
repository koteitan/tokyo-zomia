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
| DL-803 | 国土地理院 DEM5A へのアクセス間隔が50ms以上 | リクエスト前に50ms以上の sleep/delay がある | download.py のソースコードを grep し、DEM リクエスト前後に `time.sleep(0.05)` 以上の待機があることを確認 |

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
3. ブラックボックステスト (`test/blackbox/test_blackbox.py`) を実行する
4. 結果を docs/test-report.md に記録する
