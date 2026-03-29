#!/usr/bin/env python3
"""
ブラックボックステスト: ファイル構成変更・gzip圧縮対応 + 既存データ品質検証
テスト仕様: docs/test-spec.md カテゴリ 1-9 (DL-xxx) + 10-12 (RS-xxx)
"""

import gzip
import json
import math
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

passed = 0
failed = 0
results = []


def check(test_id, name, condition, detail=""):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
        print(f"  PASS: [{test_id}] {name}")
    else:
        failed += 1
        print(f"  FAIL: [{test_id}] {name} -- {detail}")
    results.append((test_id, status, name, detail if not condition else ""))


def load_gz_json(relpath):
    path = os.path.join(BASE_DIR, relpath)
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def read_file(relpath):
    path = os.path.join(BASE_DIR, relpath)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ========================================
# カテゴリ 10: ファイル構成変更
# ========================================
print("[10] ファイル構成変更")

check("RS-101", "index.html が存在する",
      os.path.isfile(os.path.join(BASE_DIR, "index.html")))
check("RS-102", "index.js が存在する",
      os.path.isfile(os.path.join(BASE_DIR, "index.js")))
check("RS-103", "style.css が存在する",
      os.path.isfile(os.path.join(BASE_DIR, "style.css")))
check("RS-104", "preview.html が削除されている",
      not os.path.exists(os.path.join(BASE_DIR, "preview.html")),
      "preview.html still exists")
check("RS-105", "preview.js が削除されている",
      not os.path.exists(os.path.join(BASE_DIR, "preview.js")),
      "preview.js still exists")
# RS-106: 旧 .geojson との共存は許容 (skip)

# ========================================
# カテゴリ 11: gzip 圧縮
# ========================================
print("[11] gzip 圧縮")

for fname, tid in [("data/rivers.geojson.gz", "RS-201"),
                   ("data/coastline.geojson.gz", "RS-202")]:
    path = os.path.join(BASE_DIR, fname)
    if os.path.isfile(path):
        with open(path, "rb") as f:
            magic = f.read(2)
        check(tid, f"{fname} が有効な gzip ファイル",
              magic == b'\x1f\x8b', f"magic={magic!r}")
    else:
        check(tid, f"{fname} が有効な gzip ファイル", False, "file missing")

for fname, tid in [("data/rivers.geojson.gz", "RS-203"),
                   ("data/coastline.geojson.gz", "RS-204")]:
    path = os.path.join(BASE_DIR, fname)
    try:
        data = load_gz_json(fname)
        check(tid, f"{fname} が解凍・パースできる",
              data.get("type") == "FeatureCollection")
    except Exception as e:
        check(tid, f"{fname} が解凍・パースできる", False, str(e))

py_src = read_file("download.py")
check("RS-205", "download.py が gzip モジュールを使用",
      "import gzip" in py_src, "import gzip not found")
check("RS-206", "download.py が gzip.open で書き込む",
      "gzip.open" in py_src, "gzip.open not found")

# RS-207: 圧縮率チェック
for fname in ["data/rivers.geojson.gz", "data/coastline.geojson.gz"]:
    path = os.path.join(BASE_DIR, fname)
    if os.path.isfile(path):
        gz_size = os.path.getsize(path)
        with gzip.open(path, "rb") as f:
            raw_size = len(f.read())
        ratio = gz_size / raw_size if raw_size > 0 else 1
        check("RS-207", f"{fname} 圧縮率 ({ratio:.1%})",
              ratio < 0.80, f"ratio={ratio:.1%} >= 80%")

# ========================================
# カテゴリ 12: フロントエンド参照整合性
# ========================================
print("[12] フロントエンド参照整合性")

html = read_file("index.html")
js = read_file("index.js")
css = read_file("style.css")
spec = read_file("docs/spec-preview.md")

check("RS-301", "index.html が style.css を参照",
      'href="style.css"' in html, "style.css link not found")
check("RS-302", "index.html が index.js を参照",
      'src="index.js"' in html, "index.js script not found")
check("RS-303", "index.html にインライン <style> がない",
      "<style>" not in html, "inline <style> found")
check("RS-304", "index.js が DecompressionStream を使用",
      "DecompressionStream" in js, "DecompressionStream not found")
check("RS-305", "index.js が .geojson.gz パスを参照",
      "rivers.geojson.gz" in js and "coastline.geojson.gz" in js,
      ".geojson.gz paths not found")
check("RS-306", "index.js が旧 .geojson パスを参照しない",
      'fetch("data/rivers.geojson")' not in js,
      "still fetches uncompressed")
check("RS-307", "index.html が有効な HTML5 文書",
      html.strip().startswith("<!DOCTYPE html")
      and "<html" in html and "<head>" in html or "<head " in html
      and "<body>" in html or "<body " in html,
      "missing HTML5 structure")
check("RS-308", "style.css が空でない",
      os.path.getsize(os.path.join(BASE_DIR, "style.css")) > 0,
      "style.css is empty")
check("RS-309", "spec-preview.md が新ファイル名を記載",
      all(s in spec for s in ["index.html", "index.js", "style.css",
                               ".geojson.gz", "DecompressionStream"]),
      "missing new file references")
check("RS-310", "spec-preview.md が旧ファイル名を記載しない",
      "preview.html" not in spec and "preview.js" not in spec,
      "still references old files")

# ========================================
# カテゴリ 1-5: 既存データ品質テスト（.gz対応版）
# ========================================

rivers = load_gz_json("data/rivers.geojson.gz")
coast = load_gz_json("data/coastline.geojson.gz")
r_features = rivers["features"]
c_features = coast["features"]

# --- 1. 対象水系の特定 ---
print("[1] 対象水系の特定")

check("DL-103", "全 Feature に空でない suikei_code が存在",
      all(f["properties"].get("suikei_code", "") != "" for f in r_features),
      "empty suikei_code found")

# --- 2. 標高300m以上フィルタリング ---
print("[2] 標高300m以上フィルタリング")

max_elevs = []
for f in r_features:
    coords = f["geometry"]["coordinates"]
    elevs = [c[2] for c in coords if len(c) >= 3]
    if elevs:
        max_elevs.append(max(elevs))

features_300 = [e for e in max_elevs if e >= 300]
overall_max = max(max_elevs) if max_elevs else 0
check("DL-202", f"300m以上到達Feature: {len(features_300)}件, 最大標高: {overall_max}m",
      len(features_300) > 0,
      f"no feature reaches 300m, max={overall_max}")

# --- 3. DEM標高付与 ---
print("[3] DEM標高付与")

all_3d = True
all_in_range = True
null_nan_count = 0
total_verts = 0

for f in r_features:
    coords = f["geometry"]["coordinates"]
    for c in coords:
        total_verts += 1
        if len(c) != 3:
            all_3d = False
            continue
        elev = c[2]
        if elev is None or (isinstance(elev, float) and math.isnan(elev)):
            null_nan_count += 1
        elif not (0 <= elev <= 4000):
            all_in_range = False

check("DL-301", f"全{total_verts}頂点が3D座標",
      all_3d, "non-3D coordinates found")
check("DL-302", "全座標の標高が0m以上4000m以下",
      all_in_range, "elevation out of range")
check("DL-303", f"null/NaN標高: {null_nan_count}件",
      null_nan_count == 0, f"{null_nan_count} null/NaN values")

# DL-304: DEMキャッシュzoom level
dem_dir = os.path.join(BASE_DIR, "cache", "dem")
if os.path.isdir(dem_dir):
    dem_files = os.listdir(dem_dir)
    all_zoom14 = all(f.startswith("14_") for f in dem_files)
    check("DL-304", f"全{len(dem_files)}ファイルがzoom level 14",
          all_zoom14, "non-14 zoom files found")
else:
    check("DL-304", "cache/dem ディレクトリ存在", False, "dir missing")

# --- 4. 海岸線の範囲 ---
print("[4] 海岸線の範囲")

check("DL-401", f"海岸線 {len(c_features)} features",
      len(c_features) > 0, "no features")

coast_verts = 0
bbox_ok = True
island_ok = True
for f in c_features:
    for c in f["geometry"]["coordinates"]:
        coast_verts += 1
        lon, lat = c[0], c[1]
        if lon < 139.155 or lon > 140.870 or lat < 34.900 or lat > 35.745:
            bbox_ok = False
        if lat < 34.9:
            island_ok = False

check("DL-402", f"全{coast_verts}座標がbbox範囲内",
      bbox_ok, "coordinates outside bbox")
check("DL-403", "島嶼部除外（緯度34.9未満なし）",
      island_ok, "lat < 34.9 found")
check("DL-404", "全 Feature の is_river_mouth が bool 型",
      all(isinstance(f["properties"].get("is_river_mouth"), bool) for f in c_features),
      "non-bool is_river_mouth found")

# --- 5. 出力 GeoJSON の形式 ---
print("[5] 出力GeoJSON形式")

check("DL-501", "rivers.geojson.gz: type == FeatureCollection",
      rivers.get("type") == "FeatureCollection")
check("DL-502", "全 Feature に必須 properties が存在",
      all(all(k in f["properties"] for k in
              ["suikei_code", "river_code", "river_name", "section_type",
               "start_node", "end_node"])
          for f in r_features),
      "missing properties")
check("DL-503", '全 Feature の geometry.type == "LineString"',
      all(f["geometry"]["type"] == "LineString" for f in r_features),
      "non-LineString found")
check("DL-504", "coastline.geojson.gz: type == FeatureCollection",
      coast.get("type") == "FeatureCollection")
check("DL-505", "全 Feature に gyosei_code, is_river_mouth が存在",
      all(all(k in f["properties"] for k in ["gyosei_code", "is_river_mouth"])
          for f in c_features),
      "missing properties")
check("DL-506", '全 Feature の geometry.type == "LineString"',
      all(f["geometry"]["type"] == "LineString" for f in c_features),
      "non-LineString found")
check("DL-507", f"全{coast_verts}座標が2D",
      all(len(c) == 2
          for f in c_features for c in f["geometry"]["coordinates"]),
      "non-2D coordinates found")

# --- 6. キャッシュ機能 ---
print("[6] キャッシュ機能")

cache_dirs = {
    "DL-601": ["cache/w05", "cache/c23", "cache/dem", "cache/wikidata"],
}
all_exist = all(os.path.isdir(os.path.join(BASE_DIR, d))
                for d in cache_dirs["DL-601"])
check("DL-601", "キャッシュディレクトリが存在",
      all_exist, "missing cache dirs")

for tid, subdir, label in [
    ("DL-602", "cache/w05", "W05 ZIP"),
    ("DL-603", "cache/c23", "C23 ZIP"),
    ("DL-604", "cache/dem", "DEM タイル"),
    ("DL-605", "cache/wikidata", "Wikidata"),
]:
    d = os.path.join(BASE_DIR, subdir)
    count = len(os.listdir(d)) if os.path.isdir(d) else 0
    check(tid, f"{label} キャッシュ: {count}ファイル",
          count > 0, f"{subdir} is empty")

# --- 8. アクセス頻度制御 ---
print("[8] アクセス頻度制御")

check("DL-801", "Wikidata SPARQL: time.sleep(1)",
      "time.sleep(1)" in py_src, "sleep(1) not found near wikidata")
check("DL-802", "W05/C23: time.sleep(1)",
      py_src.count("time.sleep(1)") >= 3,
      "fewer than 3 sleep(1) calls")
check("DL-803", "DEM5A: time.sleep(0.01)",
      "time.sleep(0.01)" in py_src, "sleep(0.01) not found")

# --- 9. エラーハンドリング ---
print("[9] エラーハンドリング")

check("DL-901", "リトライ実装 (3回, 5秒)",
      "max_retries=3" in py_src and "retry_delay=5" in py_src,
      "retry logic not found")

jp_names = [f["properties"].get("river_name", "") for f in r_features]
has_jp = any(re.search(r'[\u3040-\u9fff]', name) for name in jp_names if name)
check("DL-902", "日本語河川名が正しく含まれる (cp932)",
      has_jp, "no Japanese river names found")

# ========================================
# サマリー
# ========================================
print()
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)
