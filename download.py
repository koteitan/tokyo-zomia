#!/usr/bin/env python3
"""
ダウンロードアプリ: APIから河川・海岸線・標高データをダウンロードし、
加工して data/ にGeoJSONファイルとして出力する。
"""

import gzip
import json
import math
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict

import shapefile

# --- 定数 ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_W05 = os.path.join(BASE_DIR, "cache", "w05")
CACHE_C23 = os.path.join(BASE_DIR, "cache", "c23")
CACHE_DEM = os.path.join(BASE_DIR, "cache", "dem")
CACHE_WIKIDATA = os.path.join(BASE_DIR, "cache", "wikidata")
DATA_DIR = os.path.join(BASE_DIR, "data")

# bbox: 早川河口以東 〜 利根川河口以南
LON_MIN = 139.155
LON_MAX = 140.870
LAT_MIN = 34.900
LAT_MAX = 35.745

# 対象都道府県
TARGET_PREFS = [14, 13, 12, 11, 19, 10, 9, 8]
# 海岸線対象都道府県
COAST_PREFS = [14, 13, 12]

ZOOM = 14
DEM_URL = "https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt"
W05_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/W05/W05-08/W05-08_{pref:02d}_GML.zip"
C23_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/C23/C23-06/C23-06_{pref:02d}_GML.zip"

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# Wikidata エンティティ
SAGAMI_BAY_QID = "Q1061221"
TOKYO_BAY_QID = "Q141017"

PREF_NAMES = {
    8: "茨城", 9: "栃木", 10: "群馬", 11: "埼玉",
    12: "千葉", 13: "東京", 14: "神奈川", 19: "山梨"
}

MIN_SOURCE_ELEVATION = 300.0

# --- ユーティリティ ---


def fetch_url(url, headers=None, max_retries=3, retry_delay=5):
    """URLからデータを取得する。リトライ付き。"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (zomia download script)"}
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  リトライ {attempt+1}/{max_retries}: {e}", flush=True)
                time.sleep(retry_delay)
            else:
                raise


def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def tile_bounds(xtile, ytile, zoom):
    n = 2 ** zoom
    lon_w = xtile / n * 360.0 - 180.0
    lon_e = (xtile + 1) / n * 360.0 - 180.0
    lat_n = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ytile / n))))
    lat_s = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ytile + 1) / n))))
    return lat_n, lon_w, lat_s, lon_e


def latlon_to_pixel(lat, lon, xtile, ytile, zoom):
    lat_n, lon_w, lat_s, lon_e = tile_bounds(xtile, ytile, zoom)
    col = int((lon - lon_w) / (lon_e - lon_w) * 256)
    row = int((lat_n - lat) / (lat_n - lat_s) * 256)
    col = max(0, min(255, col))
    row = max(0, min(255, row))
    return row, col


# --- DEM ---

tile_cache = {}


def load_dem_tile(xtile, ytile):
    key = (xtile, ytile)
    if key in tile_cache:
        return tile_cache[key]

    cache_path = os.path.join(CACHE_DEM, f"{ZOOM}_{xtile}_{ytile}.txt")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            text = f.read()
    else:
        url = DEM_URL.format(z=ZOOM, x=xtile, y=ytile)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (zomia download script)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("utf-8")
            with open(cache_path, "w") as f:
                f.write(text)
            time.sleep(0.01)
        except Exception:
            tile_cache[key] = None
            return None

    grid = []
    for line in text.strip().split("\n"):
        row = []
        for val in line.split(","):
            val = val.strip()
            if val == "e" or val == "":
                row.append(None)
            else:
                try:
                    row.append(float(val))
                except ValueError:
                    row.append(None)
        grid.append(row)

    tile_cache[key] = grid
    return grid


def get_elevation(lat, lon):
    xtile, ytile = latlon_to_tile(lat, lon, ZOOM)
    grid = load_dem_tile(xtile, ytile)
    if grid is None:
        return None
    row, col = latlon_to_pixel(lat, lon, xtile, ytile, ZOOM)
    if row < len(grid) and col < len(grid[row]):
        val = grid[row][col]
        return val
    return None


# --- Step 1: Wikidata SPARQL ---


def query_wikidata_rivers(bay_qid, bay_name):
    """Wikidataから指定された湾に流入する河川名を取得する。"""
    cache_path = os.path.join(CACHE_WIKIDATA, f"{bay_qid}.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    sparql = f"""
    SELECT ?river ?riverLabel WHERE {{
      ?river wdt:P31/wdt:P279* wd:Q4022.
      ?river wdt:P403 wd:{bay_qid}.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
    }}
    """

    params = urllib.parse.urlencode({"query": sparql, "format": "json"})
    url = f"{WIKIDATA_SPARQL_URL}?{params}"

    data = fetch_url(url, headers={
        "User-Agent": "Mozilla/5.0 (zomia download script)",
        "Accept": "application/sparql-results+json"
    })
    result = json.loads(data.decode("utf-8"))

    rivers = []
    for binding in result.get("results", {}).get("bindings", []):
        label = binding.get("riverLabel", {}).get("value", "")
        if label:
            rivers.append(label)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(rivers, f, ensure_ascii=False)

    time.sleep(1)
    return rivers


def step1_identify_target_rivers():
    """Step 1: 対象水系の特定"""
    print("[Step 1/6] 対象水系の特定...", flush=True)

    sagami_rivers = query_wikidata_rivers(SAGAMI_BAY_QID, "相模湾")
    print(f"  相模湾: {len(sagami_rivers)}水系", flush=True)

    tokyo_rivers = query_wikidata_rivers(TOKYO_BAY_QID, "東京湾")
    print(f"  東京湾: {len(tokyo_rivers)}水系", flush=True)

    all_river_names = set(sagami_rivers + tokyo_rivers)
    return all_river_names


# --- Step 2: W05 データダウンロード ---


def download_w05(pref_code):
    """W05 Shapefileをダウンロードして展開する。"""
    zip_name = f"W05-08_{pref_code:02d}_GML.zip"
    zip_path = os.path.join(CACHE_W05, zip_name)
    extract_dir = os.path.join(CACHE_W05, f"{pref_code:02d}")

    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        return extract_dir

    if not os.path.exists(zip_path):
        url = W05_URL.format(pref=pref_code)
        pref_name = PREF_NAMES.get(pref_code, str(pref_code))
        print(f"  {pref_name}({pref_code:02d}): ダウンロード中...", flush=True)
        data = fetch_url(url)
        with open(zip_path, "wb") as f:
            f.write(data)
        time.sleep(1)

    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    return extract_dir


def find_shapefile(base_dir, pattern):
    """ディレクトリ内からパターンに一致するShapefileのベース名を検索する。"""
    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".shp") and pattern in f:
                results.append(os.path.join(root, f[:-4]))
    return results


def step2_download_w05():
    """Step 2: W05河川データのダウンロード"""
    print("[Step 2/6] W05河川データのダウンロード...", flush=True)

    all_streams = []
    all_nodes = []

    for pref_code in TARGET_PREFS:
        pref_name = PREF_NAMES.get(pref_code, str(pref_code))
        extract_dir = download_w05(pref_code)

        stream_files = find_shapefile(extract_dir, "Stream")
        node_files = find_shapefile(extract_dir, "RiverNode")

        stream_count = 0
        for sf_path in stream_files:
            try:
                sf = shapefile.Reader(sf_path, encoding="cp932")
                fields = [f[0] for f in sf.fields[1:]]
                for rec, shape in zip(sf.iterRecords(), sf.iterShapes()):
                    d = dict(zip(fields, rec))
                    all_streams.append((d, shape))
                    stream_count += 1
            except Exception as e:
                print(f"  警告: {sf_path} の読み込みに失敗: {e}", flush=True)

        for nf_path in node_files:
            try:
                sf = shapefile.Reader(nf_path, encoding="cp932")
                fields = [f[0] for f in sf.fields[1:]]
                for rec, shape in zip(sf.iterRecords(), sf.iterShapes()):
                    d = dict(zip(fields, rec))
                    all_nodes.append((d, shape))
            except Exception as e:
                print(f"  警告: {nf_path} の読み込みに失敗: {e}", flush=True)

        print(f"  {pref_name}({pref_code:02d}): 完了 ({stream_count}区間)", flush=True)

    return all_streams, all_nodes


# --- Step 3: フィルタリング ---


def step3_filter_rivers(all_streams, all_nodes, target_river_names):
    """Step 3: 対象河川のフィルタリング"""
    print("[Step 3/6] 対象河川のフィルタリング...", flush=True)

    total_before = len(all_streams)
    print(f"  フィルタ前: {total_before}区間", flush=True)

    # RiverNodeの標高マップを構築 (ノードID -> 標高)
    # W05_000: ノードID (例: "gb03_1400631")
    # W05_011: 標高(m)
    rivernode_elevation = {}
    for d, shape in all_nodes:
        node_id = d.get("W05_000", "")
        elev = d.get("W05_011", None)
        if node_id and elev is not None:
            try:
                rivernode_elevation[node_id] = float(elev)
            except (ValueError, TypeError):
                pass

    def get_node_elev(node_id):
        """ノードIDから標高を取得。RiverNode W05_011を優先、なければDEM。"""
        bare_id = node_id.lstrip("#")
        if bare_id in rivernode_elevation:
            return rivernode_elevation[bare_id]
        coord = node_coords.get(node_id)
        if coord:
            lat, lon = coord
            return get_elevation(lat, lon)
        return None

    # 水系名から水系コードを照合
    target_suikei_codes = set()
    for d, shape in all_streams:
        river_name = d.get("W05_004", "")
        suikei_code = d.get("W05_001", "")
        for target_name in target_river_names:
            if target_name and river_name:
                clean_target = target_name.rstrip("川").rstrip("河")
                clean_river = river_name.rstrip("川").rstrip("河")
                if clean_target == clean_river or target_name == river_name:
                    target_suikei_codes.add(suikei_code)
                    break

    # 対象水系の全区間を収集
    target_streams = [(d, shape) for d, shape in all_streams
                      if d.get("W05_001", "") in target_suikei_codes]

    # グラフ構築: ノードID -> 接続区間インデックス
    graph = defaultdict(list)
    stream_by_idx = {}
    for idx, (d, shape) in enumerate(target_streams):
        start_node = d.get("W05_009", "")
        end_node = d.get("W05_010", "")
        graph[start_node].append(idx)
        graph[end_node].append(idx)
        stream_by_idx[idx] = (d, shape, start_node, end_node)

    # ノード座標の収集（Streamデータの端点から）
    node_coords = {}
    for idx, (d, shape, start_node, end_node) in stream_by_idx.items():
        pts = shape.points
        if pts:
            if start_node:
                node_coords.setdefault(start_node, (pts[0][1], pts[0][0]))
            if end_node:
                node_coords.setdefault(end_node, (pts[-1][1], pts[-1][0]))

    # ノード次数の計算
    node_degree = defaultdict(int)
    for idx, (d, shape, start_node, end_node) in stream_by_idx.items():
        if start_node:
            node_degree[start_node] += 1
        if end_node:
            node_degree[end_node] += 1

    # 空間ノード統合: 地理的に近い端点を同一ノードとして扱う
    # W05データは都道府県境界でノードIDが不連続なため、Union-Findで統合
    BRIDGE_THRESHOLD = 0.0005  # 約56m
    BRIDGE_GRID = 0.01

    # Union-Find
    uf_parent = {}

    def uf_find(x):
        while uf_parent.get(x, x) != x:
            uf_parent[x] = uf_parent.get(uf_parent[x], uf_parent[x])
            x = uf_parent[x]
        return x

    def uf_union(a, b):
        ra, rb = uf_find(a), uf_find(b)
        if ra != rb:
            uf_parent[ra] = rb

    # 空間グリッドで近接ノードを検出・統合
    all_nodes_list = [(nid, node_coords[nid]) for nid in node_coords]
    spatial_grid = defaultdict(list)
    for nid, (lat, lon) in all_nodes_list:
        cell = (round(lat / BRIDGE_GRID), round(lon / BRIDGE_GRID))
        spatial_grid[cell].append((nid, lat, lon))

    merge_count = 0
    for nid, (lat, lon) in all_nodes_list:
        cell_y, cell_x = round(lat / BRIDGE_GRID), round(lon / BRIDGE_GRID)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for other_nid, olat, olon in spatial_grid.get((cell_y + dy, cell_x + dx), ()):
                    if other_nid <= nid:
                        continue
                    dist = math.sqrt((lat - olat) ** 2 + (lon - olon) ** 2)
                    if dist < BRIDGE_THRESHOLD:
                        if uf_find(nid) != uf_find(other_nid):
                            uf_union(nid, other_nid)
                            merge_count += 1

    # グラフを正規化ノードIDで再構築
    graph = defaultdict(list)
    for idx, (d, shape, start_node, end_node) in stream_by_idx.items():
        canon_sn = uf_find(start_node) if start_node else ""
        canon_en = uf_find(end_node) if end_node else ""
        graph[canon_sn].append(idx)
        graph[canon_en].append(idx)
        stream_by_idx[idx] = (d, shape, canon_sn, canon_en)

    # ノード座標・次数を再構築
    node_coords = {}
    for idx, (d, shape, start_node, end_node) in stream_by_idx.items():
        pts = shape.points
        if pts:
            if start_node:
                node_coords.setdefault(start_node, (pts[0][1], pts[0][0]))
            if end_node:
                node_coords.setdefault(end_node, (pts[-1][1], pts[-1][0]))

    node_degree = defaultdict(int)
    for idx, (d, shape, start_node, end_node) in stream_by_idx.items():
        if start_node:
            node_degree[start_node] += 1
        if end_node:
            node_degree[end_node] += 1

    print(f"  空間ノード統合: {merge_count}組のノードを統合", flush=True)

    # 河口候補: 次数1のノードでbbox内かつ低標高
    mouth_candidates = set()
    for node_id, coord in node_coords.items():
        lat, lon = coord
        if node_degree[node_id] == 1:
            if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX:
                elev = get_node_elev(node_id)
                if elev is not None and elev < 10:
                    mouth_candidates.add(node_id)
                elif elev is None:
                    mouth_candidates.add(node_id)

    # 河口からBFSで到達可能な全区間を収集
    reachable = set()
    visited = set(mouth_candidates)
    queue = list(mouth_candidates)
    while queue:
        node_id = queue.pop(0)
        for idx in graph.get(node_id, []):
            if idx in reachable:
                continue
            reachable.add(idx)
            d, shape, sn, en = stream_by_idx[idx]
            other = en if sn == node_id else sn
            if other and other not in visited:
                visited.add(other)
                queue.append(other)

    # 到達可能ネットワーク内のノード次数を再計算
    reach_degree = defaultdict(int)
    for idx in reachable:
        d, shape, sn, en = stream_by_idx[idx]
        reach_degree[sn] += 1
        reach_degree[en] += 1

    # 源流ノードの標高確認: 高源流(>=300m)を特定
    # DEM標高を使用（出力と一致させるため）、DEMが取得不能ならW05_011にフォールバック
    high_sources = set()
    for node_id in visited:
        if node_id not in mouth_candidates and reach_degree[node_id] == 1:
            coord = node_coords.get(node_id)
            if coord:
                lat, lon = coord
                elev = get_elevation(lat, lon)
                if elev is None:
                    elev = get_node_elev(node_id)
            else:
                elev = get_node_elev(node_id)
            if elev is not None and elev >= MIN_SOURCE_ELEVATION:
                high_sources.add(node_id)

    # 反復的リーフ枝刈り:
    # 低源流のみに繋がるブランチを繰り返し除去する
    valid = set(reachable)
    changed = True
    while changed:
        changed = False
        deg = defaultdict(int)
        for idx in valid:
            d, shape, sn, en = stream_by_idx[idx]
            deg[sn] += 1
            deg[en] += 1

        to_remove = set()
        for idx in valid:
            d, shape, sn, en = stream_by_idx[idx]
            for leaf_node in [sn, en]:
                if deg[leaf_node] == 1:
                    if leaf_node not in mouth_candidates and leaf_node not in high_sources:
                        to_remove.add(idx)
                        break

        if to_remove:
            valid -= to_remove
            changed = True

    # 高源流からの逆BFS: 300m以上の源流から到達可能な区間のみ保持
    # (仕様: 300m以上の源流から河口までのパス上の区間のみ)
    valid_graph = defaultdict(list)
    for idx in valid:
        d, shape, sn, en = stream_by_idx[idx]
        valid_graph[sn].append(idx)
        valid_graph[en].append(idx)

    reachable_from_source = set()
    src_visited = set(high_sources)
    src_queue = list(high_sources)
    while src_queue:
        node_id = src_queue.pop(0)
        for idx in valid_graph.get(node_id, []):
            if idx in reachable_from_source:
                continue
            reachable_from_source.add(idx)
            d, shape, sn, en = stream_by_idx[idx]
            other = en if sn == node_id else sn
            if other and other not in src_visited:
                src_visited.add(other)
                src_queue.append(other)

    valid &= reachable_from_source

    filtered_streams = [stream_by_idx[idx] for idx in valid]
    print(f"  フィルタ後: {len(filtered_streams)}区間", flush=True)
    return filtered_streams


# --- Step 4: DEM標高の付与 ---


def step4_add_elevation(filtered_streams):
    """Step 4: DEM標高の付与"""
    print("[Step 4/6] DEM標高の付与...", flush=True)

    # 必要なタイルを収集
    needed_tiles = set()
    for d, shape, start_node, end_node in filtered_streams:
        for pt in shape.points:
            lon, lat = pt[0], pt[1]
            tx, ty = latlon_to_tile(lat, lon, ZOOM)
            needed_tiles.add((tx, ty))

    print(f"  必要タイル数: {len(needed_tiles)}", flush=True)

    # タイルをダウンロード
    downloaded = 0
    for tx, ty in sorted(needed_tiles):
        load_dem_tile(tx, ty)
        downloaded += 1
        if downloaded % 50 == 0:
            print(f"  {downloaded}/{len(needed_tiles)} tiles...", flush=True)

    # 各区間に3D座標を付与
    features_3d = []
    for d, shape, start_node, end_node in filtered_streams:
        coords_3d = []
        for pt in shape.points:
            lon, lat = pt[0], pt[1]
            elev = get_elevation(lat, lon)
            coords_3d.append([lon, lat, elev])

        features_3d.append((d, coords_3d, start_node, end_node))

    # NoDataの補間: 端点の既知標高から線形補間
    for i, (d, coords, start_node, end_node) in enumerate(features_3d):
        # まず既知の標高を集める
        known_indices = [(j, c[2]) for j, c in enumerate(coords) if c[2] is not None]

        if not known_indices:
            # 全てNoData: 0で埋める
            for c in coords:
                c[2] = 0.0
            continue

        # 線形補間
        for j in range(len(coords)):
            if coords[j][2] is not None:
                continue
            # 前後の既知点を探す
            prev_known = None
            next_known = None
            for ki, kv in known_indices:
                if ki <= j:
                    prev_known = (ki, kv)
                if ki >= j and next_known is None:
                    next_known = (ki, kv)
            if prev_known and next_known and prev_known[0] != next_known[0]:
                ratio = (j - prev_known[0]) / (next_known[0] - prev_known[0])
                coords[j][2] = prev_known[1] + ratio * (next_known[1] - prev_known[1])
            elif prev_known:
                coords[j][2] = prev_known[1]
            elif next_known:
                coords[j][2] = next_known[1]
            else:
                coords[j][2] = 0.0

    # 丸め + 負標高をクランプ（海面付近のDEM誤差対策）
    for d, coords, start_node, end_node in features_3d:
        for c in coords:
            c[0] = round(c[0], 8)
            c[1] = round(c[1], 8)
            c[2] = round(max(0.0, c[2]), 2)

    return features_3d


# --- Step 5: 海岸線データ ---


def download_c23(pref_code):
    """C23 Shapefileをダウンロードして展開する。"""
    zip_name = f"C23-06_{pref_code:02d}_GML.zip"
    zip_path = os.path.join(CACHE_C23, zip_name)
    extract_dir = os.path.join(CACHE_C23, f"{pref_code:02d}")

    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        return extract_dir

    if not os.path.exists(zip_path):
        url = C23_URL.format(pref=pref_code)
        pref_name = PREF_NAMES.get(pref_code, str(pref_code))
        print(f"  {pref_name}({pref_code:02d}): ダウンロード中...", flush=True)
        data = fetch_url(url)
        with open(zip_path, "wb") as f:
            f.write(data)
        time.sleep(1)

    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    return extract_dir


def step5_download_coastline(river_mouths_coords=None):
    """Step 5: 海岸線データのダウンロード"""
    print("[Step 5/6] 海岸線データのダウンロード...", flush=True)

    all_coast_features = []

    for pref_code in COAST_PREFS:
        pref_name = PREF_NAMES.get(pref_code, str(pref_code))
        extract_dir = download_c23(pref_code)

        coast_files = find_shapefile(extract_dir, "Coastline")
        for sf_path in coast_files:
            try:
                sf = shapefile.Reader(sf_path, encoding="cp932")
                fields = [f[0] for f in sf.fields[1:]]
                for rec, shape in zip(sf.iterRecords(), sf.iterShapes()):
                    d = dict(zip(fields, rec))
                    all_coast_features.append((d, shape))
            except Exception as e:
                print(f"  警告: {sf_path} の読み込みに失敗: {e}", flush=True)

        print(f"  {pref_name}({pref_code:02d}): 完了", flush=True)

    # bboxフィルタリング + 島嶼部除外
    filtered = []
    for d, shape in all_coast_features:
        pts = shape.points
        if not pts:
            continue
        # 全座標がbbox内かつ緯度34.9以上か確認
        in_bbox = True
        for pt in pts:
            lon, lat = pt[0], pt[1]
            if lon < LON_MIN or lon > LON_MAX or lat < LAT_MIN or lat > LAT_MAX:
                in_bbox = False
                break
        if in_bbox:
            filtered.append((d, shape))

    # 河口判定: 河川の河口座標に近い海岸線区間
    # 空間グリッドを構築 (0.01度≒1km セル) して O(1) ルックアップ
    GRID_RES = 0.01
    THRESHOLD = 0.005  # 約500m
    mouth_grid = defaultdict(list)
    for mlat, mlon in river_mouths_coords:
        cell = (round(mlat / GRID_RES), round(mlon / GRID_RES))
        mouth_grid[cell].append((mlat, mlon))

    coast_features_out = []
    for d, shape in filtered:
        # 行政区域コード
        gyosei_code = ""
        for key in ["C23_001", "C23_002"]:
            if key in d:
                gyosei_code = str(d[key])
                break

        # 河口判定: グリッドで近傍セルのみ検索
        is_river_mouth = False
        if river_mouths_coords:
            for pt in shape.points:
                lon, lat = pt[0], pt[1]
                cell_y = round(lat / GRID_RES)
                cell_x = round(lon / GRID_RES)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        for mlat, mlon in mouth_grid.get((cell_y + dy, cell_x + dx), ()):
                            dist = math.sqrt((lat - mlat)**2 + (lon - mlon)**2)
                            if dist < THRESHOLD:
                                is_river_mouth = True
                                break
                        if is_river_mouth:
                            break
                    if is_river_mouth:
                        break
                if is_river_mouth:
                    break

        coords = [[round(pt[0], 8), round(pt[1], 8)] for pt in shape.points]
        coast_features_out.append({
            "type": "Feature",
            "properties": {
                "gyosei_code": gyosei_code,
                "is_river_mouth": is_river_mouth
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        })

    return coast_features_out


# --- Step 6: GeoJSON出力 ---


def step6_output(features_3d, coast_features):
    """Step 6: GeoJSON出力"""
    print("[Step 6/6] GeoJSON出力...", flush=True)

    # rivers.geojson
    river_features = []
    for d, coords, start_node, end_node in features_3d:
        feature = {
            "type": "Feature",
            "properties": {
                "suikei_code": str(d.get("W05_001", "")),
                "river_code": str(d.get("W05_002", "")),
                "river_name": str(d.get("W05_004", "")),
                "section_type": str(d.get("W05_003", "")),
                "start_node": str(start_node),
                "end_node": str(end_node)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }
        river_features.append(feature)

    rivers_geojson = {
        "type": "FeatureCollection",
        "features": river_features
    }

    rivers_path = os.path.join(DATA_DIR, "rivers.geojson.gz")
    rivers_json = json.dumps(rivers_geojson, ensure_ascii=False).encode("utf-8")
    with gzip.open(rivers_path, "wb") as f:
        f.write(rivers_json)

    total_vertices = sum(len(f["geometry"]["coordinates"]) for f in river_features)
    raw_size = len(rivers_json)
    gz_size = os.path.getsize(rivers_path)
    print(f"  data/rivers.geojson.gz: {len(river_features)} features, {total_vertices} vertices", flush=True)
    print(f"    raw={raw_size} bytes, gz={gz_size} bytes ({gz_size*100//raw_size}%)", flush=True)

    # coastline.geojson.gz
    coastline_geojson = {
        "type": "FeatureCollection",
        "features": coast_features
    }

    coast_path = os.path.join(DATA_DIR, "coastline.geojson.gz")
    coast_json = json.dumps(coastline_geojson, ensure_ascii=False).encode("utf-8")
    with gzip.open(coast_path, "wb") as f:
        f.write(coast_json)

    coast_vertices = sum(len(f["geometry"]["coordinates"]) for f in coast_features)
    raw_size = len(coast_json)
    gz_size = os.path.getsize(coast_path)
    print(f"  data/coastline.geojson.gz: {len(coast_features)} features, {coast_vertices} vertices", flush=True)
    print(f"    raw={raw_size} bytes, gz={gz_size} bytes ({gz_size*100//raw_size}%)", flush=True)


# --- Main ---


def main():
    # ディレクトリ作成
    for d in [CACHE_W05, CACHE_C23, CACHE_DEM, CACHE_WIKIDATA, DATA_DIR]:
        os.makedirs(d, exist_ok=True)

    # 既存のdem_cacheからキャッシュをコピー
    old_dem_cache = os.path.join(BASE_DIR, "dem_cache")
    if os.path.isdir(old_dem_cache):
        for fname in os.listdir(old_dem_cache):
            src = os.path.join(old_dem_cache, fname)
            dst = os.path.join(CACHE_DEM, fname)
            if not os.path.exists(dst) and os.path.isfile(src):
                shutil.copy2(src, dst)

    # Step 1: 対象水系の特定
    target_river_names = step1_identify_target_rivers()

    # Step 2: W05河川データのダウンロード
    all_streams, all_nodes = step2_download_w05()

    # Step 3: 対象河川のフィルタリング
    filtered_streams = step3_filter_rivers(all_streams, all_nodes, target_river_names)

    # Step 4: DEM標高の付与
    features_3d = step4_add_elevation(filtered_streams)

    # 河口座標の収集（海岸線の河口判定用）
    river_mouths = []
    for d, coords, start_node, end_node in features_3d:
        if coords:
            # 最も標高が低い端点を河口候補とする
            start_elev = coords[0][2]
            end_elev = coords[-1][2]
            if start_elev <= end_elev:
                river_mouths.append((coords[0][1], coords[0][0]))
            else:
                river_mouths.append((coords[-1][1], coords[-1][0]))

    # Step 5: 海岸線データのダウンロード
    coast_features = step5_download_coastline(river_mouths)

    # Step 6: GeoJSON出力
    step6_output(features_3d, coast_features)

    print("完了", flush=True)


if __name__ == "__main__":
    main()
