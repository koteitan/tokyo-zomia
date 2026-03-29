# zomia

相模湾・東京湾に注ぐ河川水系と海岸線の3Dビューア。

## 操作方法

ブラウザで `index.html` を開いてください（ローカルHTTPサーバー経由）。

| 操作 | 動作 |
|------|------|
| 左ドラッグ | 回転 |
| 右ドラッグ | パン |
| マウスホイール | ズーム |
| 標高スケール スライダー | 標高の誇張倍率を変更（1x〜50x） |
| 端点表示 チェックボックス | 河川の分岐・合流点の表示/非表示 |
| 海岸線表示 チェックボックス | 海岸線の表示/非表示 |

## データ著作権

本アプリが使用するデータは以下の出典に基づいています。

- 河川データ: 国土交通省「[国土数値情報（河川データ）](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-W05.html)」を加工して作成
- 海岸線データ: 国土交通省「[国土数値情報（海岸線データ）](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-C23.html)」を加工して作成
- 標高データ: [国土地理院](https://www.gsi.go.jp/)「数値標高モデル（DEM5A）」を加工して作成
- 水系情報: [Wikidata](https://www.wikidata.org/) を利用

各データは「[公共データ利用規約（第1.0版）](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)」に基づき利用しています。

## 開発者向け

### ダウンロード・解析

#### 要件

- Linux / WSL2
- Python 3.10+
- `pyshp` パッケージ (`pip install pyshp`)

#### 方法

```bash
python3 download.py
```

以下のデータが `data/` に出力されます:

- `data/rivers.geojson.gz` — 対象河川の3Dポリライン（gzip圧縮GeoJSON）
- `data/coastline.geojson.gz` — 海岸線の2Dポリライン（gzip圧縮GeoJSON）

キャッシュは `cache/` に保存され、2回目以降の実行は高速です。

#### download.py フローチャート

```mermaid
flowchart TD
    Start([download.py 実行]) --> S1

    S1["Step 1: 対象水系の特定"]
    S1 --> S1a["Wikidata SPARQL で\n相模湾・東京湾に流入する\n河川名を取得"]
    S1a --> S2

    S2["Step 2: W05 河川データのダウンロード"]
    S2 --> S2a["対象8都県の\nStream.shp + RiverNode.shp\nをダウンロード"]
    S2a --> S2b["河川名で水系域コードを照合"]
    S2b --> S3

    S3["Step 3: 対象河川のフィルタリング"]
    S3 --> S3a["bbox内の河口ノードを特定"]
    S3a --> S3b["河口から上流へグラフ探索"]
    S3b --> S3c{"源流の標高\n>= 300m?"}
    S3c -- Yes --> S3d["経路上の区間を保持"]
    S3c -- No --> S3e["区間を除外"]
    S3d --> S4
    S3e --> S4

    S4["Step 4: DEM 標高の付与"]
    S4 --> S4a["各頂点の座標から\nDEM5A タイルを取得\n(zoom=14)"]
    S4a --> S4b{"DEM値が\n有効?"}
    S4b -- Yes --> S4c["標高をそのまま使用"]
    S4b -- "NoData" --> S4d["RiverNode端点標高で\n線形補間"]
    S4c --> S5
    S4d --> S5

    S5["Step 5: 海岸線データのダウンロード"]
    S5 --> S5a["神奈川・東京・千葉の\nC23 Shapefile をダウンロード"]
    S5a --> S5b["bbox内の区間を抽出\n島嶼部を除外"]
    S5b --> S5c["河口座標との近接判定で\nis_river_mouth を設定"]
    S5c --> S6

    S6["Step 6: GeoJSON 出力"]
    S6 --> S6a["data/rivers.geojson.gz\n3D河川ポリライン"]
    S6 --> S6b["data/coastline.geojson.gz\n2D海岸線ポリライン"]
    S6a --> End
    S6b --> End([完了])
```

### ファイル構成

```
index.html              Web アプリ (HTML)
index.js                Web アプリ (JavaScript, WebGL描画)
style.css               Web アプリ (CSS)
download.py             ダウンロード・解析スクリプト
data/
  rivers.geojson.gz     河川 3D ポリライン (gzip)
  coastline.geojson.gz  海岸線 2D ポリライン (gzip)
cache/                  API レスポンスキャッシュ
  w05/                  国土数値情報 河川データ
  c23/                  国土数値情報 海岸線データ
  dem/                  国土地理院 DEM5A タイル
  wikidata/             Wikidata SPARQL レスポンス
logs/                   実行ログ
docs/
  spec.md               仕様書
  spec-download.md      ダウンロードアプリ詳細仕様
  spec-preview.md       プレビューアプリ詳細仕様
  test-spec.md          テスト仕様書
  test-report.md        テスト結果レポート
test/
  white/                ホワイトボックステスト
  blackbox/             ブラックボックステスト
```
