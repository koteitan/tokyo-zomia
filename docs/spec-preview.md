# プレビューアプリ 詳細仕様書

## 概要
`index.html` + `index.js` + `style.css` で、`data/rivers.geojson.gz` と `data/coastline.geojson.gz` を
3D表示するWebアプリ。

## ファイル構成
- `index.html` — HTML/UI
- `style.css` — スタイルシート
- `index.js` — WebGL描画ロジック + gzip解凍

## 依存
- 外部ライブラリなし（素のWebGL + DecompressionStream API のみ）
- データは `data/rivers.geojson.gz`, `data/coastline.geojson.gz` をfetchし、DecompressionStream("gzip")で解凍して読み込む

---

## データ読み込み
- `data/rivers.geojson.gz` — gzip圧縮されたGeoJSON FeatureCollection、各FeatureはLineStringで3D座標 `[lon, lat, elev]`
- `data/coastline.geojson.gz` — gzip圧縮されたGeoJSON FeatureCollection、各FeatureはLineStringで2D座標 `[lon, lat]`
- DecompressionStream APIを使用してブラウザ側でストリーム解凍（外部ライブラリ不要）

---

## 座標変換
- 経緯度→メートル換算（中心緯度での近似）
- 正規化: 全データの範囲に基づいて [-1, 1] 程度に正規化
- 標高: `elevScale` スライダーで倍率を制御（デフォルト10x）

---

## 描画仕様

### 河川
- WebGL `LINES` でポリラインを描画
- 色: 標高に応じたグラデーション（青=低 → 緑 → 黄 → 赤=高）
- 端点: 白い点（`POINTS`, size=4）、表示/非表示をチェックボックスで切り替え
- マウスホバー: 最近傍ポリラインの河川名をツールチップ表示、隣接セグメントを白色ハイライト

### 海岸線
- WebGL `LINES` でポリラインを描画
- 色: 水色 `(0.3, 0.6, 0.8)`
- 河口区間（`is_river_mouth == true`）は黄色 `(1, 1, 0.3)`
- 標高は0として描画（海面）
- 表示/非表示をチェックボックスで切り替え

### グリッド
- XZ平面に参照用グリッドを描画
- 色: 暗灰色 `(0.2, 0.2, 0.2)`

---

## カメラ操作
| 操作 | 動作 |
|------|------|
| 左ドラッグ | 回転（rotX, rotY） |
| 右ドラッグ | パン（panX, panY） |
| ホイール | ズーム（0.1〜20倍） |

初期カメラ: `rotX=-0.6, rotY=0.4, zoom=2.5`

---

## UI
- 情報パネル（左上）: タイトル、操作方法
- コントロールパネル（右上）:
  - 標高スケール: range スライダー (1〜50, デフォルト10)
  - 端点表示: チェックボックス
  - 海岸線表示: チェックボックス

---

## マウスホバー・ハイライト

### 隣接グラフ
- 各セグメントの `start_node` / `end_node` プロパティからノード→セグメントの隣接マップを構築
- 各ノードの次数（degree）を計算

### 最近傍セグメント検索
- マウス座標から、全セグメントの各線分をスクリーン空間に投影し、点-線分距離で最近傍を検索
- 閾値: 15px 以内

### フラッドフィルハイライト
- 最近傍セグメントから、隣接グラフに沿って degree==2 のノードを通過して連続セグメントを収集
- degree!=2（分岐・合流・端点）のノードで探索を停止
- ハイライト色: 白 `(1, 1, 1)`

### ツールチップ
- `#tooltip` 要素に河川名を表示
- マウス位置の右下 12px にオフセット
- 河川名が空の場合は「(名称不明)」を表示
- マウスが離れるかドラッグ中はツールチップ非表示

---

## シェーダー
- 頂点シェーダー: MVP行列変換、ポイントサイズ
- フラグメントシェーダー: varying色をそのまま出力

---

## パフォーマンス要件
- 河川〜5000区間 + 海岸線〜1500区間を60fps以上で描画
- elevScale変更時にジオメトリを再構築（バッファ再アップロード）
