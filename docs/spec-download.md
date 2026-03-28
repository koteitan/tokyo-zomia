# ダウンロードアプリ 詳細仕様書

## 概要
`download.py` を実行すると、APIから河川・海岸線・標高データをダウンロードし、
加工して `data/` にGeoJSONファイルとして出力する。

## 実行環境
- Python 3.10+
- Linux/WSL2
- 依存パッケージ: `pyshp` (shapefile読み込み)

## 出力ファイル
- `data/rivers.geojson` — 対象源流河川の3Dポリライン
- `data/coastline.geojson` — 指定範囲の海岸線2Dポリライン

---

## 指定範囲
神奈川県早川河口以東、かつ利根川河口以南の矩形(bbox)。

| 境界 | 座標 | 根拠 |
|------|------|------|
| 西端(lon_min) | 139.155 | 早川河口の経度 |
| 東端(lon_max) | 140.870 | 利根川河口(銚子)の経度 |
| 北端(lat_max) | 35.745 | 利根川河口の緯度 |
| 南端(lat_min) | 34.900 | 三浦半島・房総半島南端を含む |

---

## 処理フロー

### Step 1: 対象水系の特定

1. Wikidata SPARQL API で相模湾(Q1061221)・東京湾(Q141017)に流入する河川を取得
2. 各河川の名前から、国土数値情報W05の水系域コード(W05_001)を照合
3. 対象となる都道府県を特定（神奈川14, 東京13, 千葉12, 埼玉11, 山梨19, 群馬10, 栃木09, 茨城08）

### Step 2: W05河川データのダウンロード

1. 対象都道府県のW05 Shapefileをダウンロード
   - URL: `https://nlftp.mlit.go.jp/ksj/gml/data/W05/W05-08/W05-08_{pref:02d}_GML.zip`
   - キャッシュ: `cache/w05/` に保存し、既存なら再ダウンロードしない
2. 各都道府県のStream.shpとRiverNode.shpを読み込み

### Step 3: 対象河川のフィルタリング

1. 全水系のRiverNodeから、指定範囲内の河口ノード(bbox内で標高が最低の端点)を特定
2. 河口ノードから上流に向かってグラフを辿り、全ての上流区間を収集
3. 各区間の源流ノード（最上流端点）の標高を確認
4. **標高300m以上の源流ノード**を持つ経路上の区間のみを残す
5. 標高300m未満の源流からしか到達できない区間は除外

### Step 4: DEM標高の付与

1. フィルタリング後の区間の全頂点について、国土地理院DEM5Aタイルから標高を取得
   - URL: `https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt`
   - zoom level: 14
   - キャッシュ: `cache/dem/` に保存
   - アクセス間隔: 50ms以上
2. DEM NoData（水面・欠損）の頂点は、RiverNodeの端点標高で線形補間

### Step 5: 海岸線データのダウンロード

1. 対象都道府県(神奈川14, 東京13, 千葉12)のC23 Shapefileをダウンロード
   - URL: `https://nlftp.mlit.go.jp/ksj/gml/data/C23/C23-06/C23-06_{pref:02d}_GML.zip`
   - キャッシュ: `cache/c23/` に保存
2. 指定範囲のbbox内の区間のみを抽出
3. 島嶼部(伊豆諸島等)を除外（緯度34.9未満を除外）

### Step 6: GeoJSON出力

#### data/rivers.geojson
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "suikei_code": "830307",
        "river_code": "8303070001",
        "river_name": "相模川",
        "section_type": "1",
        "start_node": "#gb03_...",
        "end_node": "#gb03_..."
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [[139.0, 35.0, 100.0], ...]
      }
    }
  ]
}
```

#### data/coastline.geojson
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "gyosei_code": "14101",
        "is_river_mouth": false
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [[139.0, 35.0], ...]
      }
    }
  ]
}
```

---

## 進捗表示
標準出力に以下の形式で進捗を表示する:
```
[Step 1/6] 対象水系の特定...
  相模湾: 15水系
  東京湾: 36水系
[Step 2/6] W05河川データのダウンロード...
  神奈川(14): ダウンロード中...
  神奈川(14): 完了 (2305区間)
  ...
[Step 3/6] 対象河川のフィルタリング...
  フィルタ前: 12000区間
  フィルタ後: 5000区間
[Step 4/6] DEM標高の付与...
  必要タイル数: 800
  50/800 tiles...
  ...
[Step 5/6] 海岸線データのダウンロード...
[Step 6/6] GeoJSON出力...
  data/rivers.geojson: 5000 features, 150000 vertices
  data/coastline.geojson: 1500 features, 70000 vertices
完了
```

---

## キャッシュ構成
```
cache/
  w05/          # W05 ZIPファイル
  c23/          # C23 ZIPファイル
  dem/          # DEM5Aタイル (14_{x}_{y}.txt)
  wikidata/     # Wikidata SPARQLレスポンス (JSON)
```
2回目以降の実行ではキャッシュを使用し、APIアクセスを最小化する。

---

## アクセス頻度制御
| API | 間隔 |
|-----|------|
| Wikidata SPARQL | 1秒以上 |
| 国土数値情報 (W05/C23) | 1秒以上 |
| 国土地理院 DEM5A | 50ms以上 |

---

## エラーハンドリング
- ネットワークエラー: 3回リトライ（間隔5秒）
- DEM NoData: RiverNode標高で補間（前述）
- Shapefile読み込みエラー: エンコーディング cp932 を使用
