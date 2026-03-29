#!/usr/bin/env python3
"""
ブラックボックステスト: グラフ構造検証 — フィルタリングの完全性
テスト仕様: docs/test-spec.md カテゴリ 19 (GR-xxx)

仕様: 「標高300m以上の源流から、指定範囲の河口に繋がるまでの経路に存在するあらゆる河川のポリライン」

構造テスト:
全セグメントがノードグラフ上で河口から到達可能であることを検証する。
到達不能セグメントが存在する場合、グラフが不連結 = フィルタリングバグ。
"""

import gzip
import json
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# bbox (spec-download.md)
LON_MIN, LON_MAX = 139.155, 140.870
LAT_MIN, LAT_MAX = 34.900, 35.745

passed = 0
failed = 0
results = []


def check(test_id, name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: [{test_id}] {name}")
    else:
        failed += 1
        print(f"  FAIL: [{test_id}] {name} -- {detail}")
    results.append((test_id, "PASS" if condition else "FAIL", name,
                     detail if not condition else ""))


def load_gz_json(relpath):
    path = os.path.join(BASE_DIR, relpath)
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


# ========================================
# データ読み込み
# ========================================
rivers = load_gz_json("data/rivers.geojson.gz")
features = rivers["features"]

print("[19] グラフ構造検証 — フィルタリングの完全性")
print(f"  データ: {len(features)} features")

# ========================================
# GR-1xx: グラフ構築
# ========================================
print()
print("[GR-1] グラフ構築")

# ノード→セグメント隣接マップ
node_to_segs = defaultdict(set)
seg_nodes = {}  # seg_index -> (start_node, end_node)

for i, f in enumerate(features):
    sn = f["properties"].get("start_node", "")
    en = f["properties"].get("end_node", "")
    seg_nodes[i] = (sn, en)
    if sn:
        node_to_segs[sn].add(i)
    if en:
        node_to_segs[en].add(i)

# ノード次数
node_degree = {}
for node_id, seg_set in node_to_segs.items():
    node_degree[node_id] = len(seg_set)

check("GR-101", f"ノード数: {len(node_to_segs)}",
      len(node_to_segs) > 0, "no nodes")
check("GR-102", f"セグメント数: {len(features)}",
      len(features) > 0, "no features")

# ========================================
# GR-2xx: 河口ノードの特定
# ========================================
print()
print("[GR-2] 河口ノードの特定")

# ノード座標: 各セグメントの端点座標からノードIDの座標を取得
node_coords = {}  # node_id -> (lon, lat, elev)
for i, f in enumerate(features):
    coords = f["geometry"]["coordinates"]
    sn, en = seg_nodes[i]
    if coords and sn and sn not in node_coords:
        c = coords[0]
        node_coords[sn] = (c[0], c[1], c[2] if len(c) >= 3 else 0)
    if coords and en and en not in node_coords:
        c = coords[-1]
        node_coords[en] = (c[0], c[1], c[2] if len(c) >= 3 else 0)

# 河口ノード: 次数1 + bbox 内 + 低標高 (<10m)
mouth_nodes = set()
for node_id, deg in node_degree.items():
    if deg != 1:
        continue
    if node_id not in node_coords:
        continue
    lon, lat, elev = node_coords[node_id]
    if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX and elev < 10:
        mouth_nodes.add(node_id)

check("GR-201", f"河口ノード数: {len(mouth_nodes)}",
      len(mouth_nodes) > 0, "no river mouth nodes found")

# bbox 内の次数1ノード（河口候補の母集合）
deg1_in_bbox = sum(1 for nid, deg in node_degree.items()
                   if deg == 1 and nid in node_coords
                   and LON_MIN <= node_coords[nid][0] <= LON_MAX
                   and LAT_MIN <= node_coords[nid][1] <= LAT_MAX)
check("GR-202", f"bbox 内の次数1ノード: {deg1_in_bbox}",
      deg1_in_bbox > 0, "no degree-1 nodes in bbox")

# ========================================
# GR-3xx: 河口からの到達可能性 (BFS)
# ========================================
print()
print("[GR-3] 河口からの到達可能性")

# BFS: 河口ノードから全到達可能セグメントを収集
reachable_segs = set()
visited_nodes = set(mouth_nodes)
queue = list(mouth_nodes)

while queue:
    node_id = queue.pop(0)
    for seg_idx in node_to_segs.get(node_id, set()):
        if seg_idx in reachable_segs:
            continue
        reachable_segs.add(seg_idx)
        sn, en = seg_nodes[seg_idx]
        for other in [sn, en]:
            if other and other not in visited_nodes:
                visited_nodes.add(other)
                queue.append(other)

total_segs = len(features)
unreachable_segs = set(range(total_segs)) - reachable_segs
unreachable_count = len(unreachable_segs)

check("GR-301",
      f"河口から到達可能セグメント: {len(reachable_segs)}/{total_segs}",
      len(reachable_segs) == total_segs,
      f"{unreachable_count} segments unreachable from river mouths")

check("GR-302",
      f"到達不能セグメント: {unreachable_count}",
      unreachable_count == 0,
      f"{unreachable_count} orphaned segments detected")

# 到達可能率
reach_pct = len(reachable_segs) / total_segs * 100 if total_segs > 0 else 0
check("GR-303",
      f"到達可能率: {reach_pct:.1f}%",
      reach_pct == 100.0,
      f"{reach_pct:.1f}% < 100%")

# ========================================
# GR-4xx: 不到達セグメントの診断
# ========================================
print()
print("[GR-4] 不到達セグメントの診断")

if unreachable_segs:
    # 不到達セグメントの水系コードを集計
    orphan_suikei = defaultdict(int)
    for si in unreachable_segs:
        code = features[si]["properties"].get("suikei_code", "unknown")
        orphan_suikei[code] += 1

    # 不到達セグメントの座標範囲
    orphan_lat_min = orphan_lat_max = orphan_lon_min = orphan_lon_max = None
    for si in unreachable_segs:
        for c in features[si]["geometry"]["coordinates"]:
            lat, lon = c[1], c[0]
            if orphan_lat_min is None or lat < orphan_lat_min:
                orphan_lat_min = lat
            if orphan_lat_max is None or lat > orphan_lat_max:
                orphan_lat_max = lat
            if orphan_lon_min is None or lon < orphan_lon_min:
                orphan_lon_min = lon
            if orphan_lon_max is None or lon > orphan_lon_max:
                orphan_lon_max = lon

    top_orphans = sorted(orphan_suikei.items(), key=lambda x: -x[1])[:5]
    orphan_summary = ", ".join(f"{code}:{cnt}" for code, cnt in top_orphans)

    check("GR-401", "不到達セグメントが存在しない", False,
          f"orphans by suikei: {orphan_summary}")
    print(f"    不到達セグメント座標範囲:")
    print(f"      lat: {orphan_lat_min:.4f} - {orphan_lat_max:.4f}")
    print(f"      lon: {orphan_lon_min:.4f} - {orphan_lon_max:.4f}")
    print(f"    不到達セグメントの水系 (上位5):")
    for code, cnt in top_orphans:
        name = ""
        for si in unreachable_segs:
            if features[si]["properties"].get("suikei_code") == code:
                name = features[si]["properties"].get("river_name", "")
                if name:
                    break
        print(f"      {code}: {cnt} segments ({name})")
else:
    check("GR-401", "不到達セグメントが存在しない", True)

# ========================================
# GR-5xx: 源流ノードの検証
# ========================================
print()
print("[GR-5] 源流ノードの検証")

# 源流ノード: 次数1 で河口でないノード
source_nodes = set()
for node_id, deg in node_degree.items():
    if deg == 1 and node_id not in mouth_nodes:
        source_nodes.add(node_id)

check("GR-501", f"源流ノード数: {len(source_nodes)}",
      len(source_nodes) > 0, "no source nodes found")

# 300m以上の源流ノード
high_sources = set()
for nid in source_nodes:
    if nid in node_coords:
        lon, lat, elev = node_coords[nid]
        if elev >= 300:
            high_sources.add(nid)

check("GR-502", f"標高300m以上の源流ノード: {len(high_sources)}",
      len(high_sources) > 0, "no high-elevation source nodes")

# 仕様: 全セグメントは300m以上源流から河口に至る経路上にある
# → 各セグメントの属する連結成分に300m以上源流と河口の両方が含まれるはず
# (河口BFS で全セグメントが到達可能であることは GR-301 で検証済み)
# 追加: 300m以上源流からのBFS でも全セグメントが到達可能か

reachable_from_sources = set()
visited_src = set(high_sources)
queue_src = list(high_sources)

while queue_src:
    node_id = queue_src.pop(0)
    for seg_idx in node_to_segs.get(node_id, set()):
        if seg_idx in reachable_from_sources:
            continue
        reachable_from_sources.add(seg_idx)
        sn, en = seg_nodes[seg_idx]
        for other in [sn, en]:
            if other and other not in visited_src:
                visited_src.add(other)
                queue_src.append(other)

check("GR-503",
      f"300m以上源流から到達可能セグメント: {len(reachable_from_sources)}/{total_segs}",
      len(reachable_from_sources) == total_segs,
      f"{total_segs - len(reachable_from_sources)} unreachable from 300m+ sources")

# ========================================
# GR-6xx: 双方向到達可能性（源流→河口パスの存在）
# ========================================
print()
print("[GR-6] 双方向到達可能性")

# 河口と300m源流の両方から到達可能 = パスが存在
both_reachable = reachable_segs & reachable_from_sources
check("GR-601",
      f"河口・源流両方から到達可能: {len(both_reachable)}/{total_segs}",
      len(both_reachable) == total_segs,
      f"{total_segs - len(both_reachable)} segments not on a source-to-mouth path")

# ========================================
# サマリー
# ========================================
print()
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)
