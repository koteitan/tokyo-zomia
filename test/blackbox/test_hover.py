#!/usr/bin/env python3
"""
ブラックボックステスト: マウスホバー・ハイライト機能
テスト仕様: docs/spec-preview.md「マウスホバー・ハイライト」セクション

自動検証可能な範囲:
- GeoJSON properties にホバー機能に必要なフィールドが揃っているか
- start_node/end_node から隣接グラフが正しく構築されるか
- ノード次数の判定が正しいか（分岐・合流・端点の存在）
- フラッドフィルが degree!=2 で停止するか
- index.js にホバー関連コードが仕様通り含まれるか
"""

import gzip
import json
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def read_file(relpath):
    path = os.path.join(BASE_DIR, relpath)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ========================================
# データ読み込み
# ========================================
rivers = load_gz_json("data/rivers.geojson.gz")
features = rivers["features"]
js = read_file("index.js")
spec = read_file("docs/spec-preview.md")

# ========================================
# HV-1xx: GeoJSON properties の完全性
# ========================================
print("[HV-1] GeoJSON properties の完全性")

has_start = all("start_node" in f["properties"] for f in features)
check("HV-101", "全 Feature に start_node プロパティが存在", has_start,
      "start_node missing in some features")

has_end = all("end_node" in f["properties"] for f in features)
check("HV-102", "全 Feature に end_node プロパティが存在", has_end,
      "end_node missing in some features")

has_name = all("river_name" in f["properties"] for f in features)
check("HV-103", "全 Feature に river_name プロパティが存在", has_name,
      "river_name missing in some features")

non_empty_sn = sum(1 for f in features
                   if f["properties"].get("start_node", "") != "")
check("HV-104", f"空でない start_node: {non_empty_sn}/{len(features)}",
      non_empty_sn > 0, "all start_node are empty")

non_empty_en = sum(1 for f in features
                   if f["properties"].get("end_node", "") != "")
check("HV-105", f"空でない end_node: {non_empty_en}/{len(features)}",
      non_empty_en > 0, "all end_node are empty")

# ========================================
# HV-2xx: 隣接グラフ構築
# ========================================
print("[HV-2] 隣接グラフ構築")

node_to_segs = defaultdict(list)
node_degree = defaultdict(int)

for i, f in enumerate(features):
    sn = f["properties"].get("start_node", "")
    en = f["properties"].get("end_node", "")
    if sn:
        node_to_segs[sn].append(i)
        node_degree[sn] += 1
    if en:
        node_to_segs[en].append(i)
        node_degree[en] += 1

check("HV-201", f"ノード数: {len(node_to_segs)}",
      len(node_to_segs) > 0, "no nodes found")

check("HV-202", f"セグメント数: {len(features)}",
      len(features) > 0, "no features")

# 各セグメントは2つのノード（start/end）を持つ → グラフに2回登場するはず
segs_with_both = sum(1 for f in features
                     if f["properties"].get("start_node", "") != ""
                     and f["properties"].get("end_node", "") != "")
check("HV-203", f"start_node と end_node 両方あるセグメント: {segs_with_both}/{len(features)}",
      segs_with_both > len(features) * 0.9,
      f"only {segs_with_both} have both nodes")

# ノードから辿れるセグメントの整合性: node_to_segs[node] の各 seg は
# そのノードを start_node か end_node として持つ
consistency_ok = True
for node_id, seg_indices in node_to_segs.items():
    for si in seg_indices:
        props = features[si]["properties"]
        if props.get("start_node") != node_id and props.get("end_node") != node_id:
            consistency_ok = False
            break
    if not consistency_ok:
        break
check("HV-204", "隣接マップの整合性（ノード↔セグメント）",
      consistency_ok, "inconsistent node-segment mapping")

# ========================================
# HV-3xx: ノード次数の判定
# ========================================
print("[HV-3] ノード次数の判定")

deg_counts = defaultdict(int)
for d in node_degree.values():
    deg_counts[d] += 1

deg_1 = deg_counts.get(1, 0)  # 端点（源流・河口）
deg_2 = deg_counts.get(2, 0)  # 通過点
deg_3plus = sum(c for d, c in deg_counts.items() if d >= 3)  # 分岐・合流

check("HV-301", f"degree==1（端点）: {deg_1}ノード",
      deg_1 > 0, "no degree-1 nodes (sources/mouths)")

check("HV-302", f"degree==2（通過点）: {deg_2}ノード",
      deg_2 > 0, "no degree-2 nodes")

check("HV-303", f"degree>=3（分岐・合流）: {deg_3plus}ノード",
      deg_3plus > 0, "no branching/merging nodes")

check("HV-304", "degree 分布が妥当（端点 < 通過点）",
      deg_1 < deg_2,
      f"deg1={deg_1} >= deg2={deg_2}")

# 最大次数の確認（通常は10程度まで）
max_deg = max(node_degree.values()) if node_degree else 0
check("HV-305", f"最大次数: {max_deg}（妥当範囲 <= 20）",
      1 <= max_deg <= 20,
      f"max_degree={max_deg}")

# ========================================
# HV-4xx: フラッドフィルのシミュレーション
# ========================================
print("[HV-4] フラッドフィルのシミュレーション")


def flood_fill(start_idx):
    """仕様通りのフラッドフィル: degree==2 を通過、degree!=2 で停止"""
    result = {start_idx}
    queue = [start_idx]
    while queue:
        idx = queue.pop()
        props = features[idx]["properties"]
        for node_id in [props.get("start_node", ""), props.get("end_node", "")]:
            if not node_id or node_degree.get(node_id, 0) != 2:
                continue
            for neighbor in node_to_segs.get(node_id, []):
                if neighbor not in result:
                    result.add(neighbor)
                    queue.append(neighbor)
    return result


# フラッドフィルが有限集合を返すか（無限ループしないか）
test_idx = 0
fill_result = flood_fill(test_idx)
check("HV-401", f"フラッドフィルが有限集合を返す（セグメント0から: {len(fill_result)}件）",
      0 < len(fill_result) <= len(features),
      f"size={len(fill_result)}")

# フラッドフィル結果が開始セグメントを含む
check("HV-402", "フラッドフィル結果に開始セグメントが含まれる",
      test_idx in fill_result, "start segment not in result")

# フラッドフィル結果の境界ノードは degree!=2
boundary_ok = True
for idx in fill_result:
    props = features[idx]["properties"]
    for node_id in [props.get("start_node", ""), props.get("end_node", "")]:
        if not node_id:
            continue
        if node_degree.get(node_id, 0) == 2:
            # degree==2 のノードを経由 → その先の隣接セグメントも fill_result に含まれるはず
            for neighbor in node_to_segs.get(node_id, []):
                if neighbor not in fill_result:
                    boundary_ok = False
                    break
        if not boundary_ok:
            break
    if not boundary_ok:
        break
check("HV-403", "フラッドフィルの boundary: degree==2 のノードの先は全て含まれる",
      boundary_ok, "flood fill missed segments through degree-2 nodes")

# 複数の開始点でフラッドフィルを検証
import random
random.seed(42)
sample_indices = random.sample(range(len(features)), min(20, len(features)))
all_fills_valid = True
for si in sample_indices:
    result = flood_fill(si)
    if si not in result or len(result) == 0 or len(result) > len(features):
        all_fills_valid = False
        break
check("HV-404", f"20サンプルのフラッドフィルが全て妥当",
      all_fills_valid, "invalid flood fill result")

# ========================================
# HV-5xx: index.js ホバー関連コード
# ========================================
print("[HV-5] index.js ホバー関連コード")

check("HV-501", "nodeToSegs 隣接マップ構築コードが存在",
      "nodeToSegs" in js, "nodeToSegs not found")

check("HV-502", "nodeDegree 次数計算コードが存在",
      "nodeDegree" in js, "nodeDegree not found")

check("HV-503", "floodFillSegments 関数が存在",
      "floodFillSegments" in js, "floodFillSegments not found")

check("HV-504", "findNearestSegment 関数が存在",
      "findNearestSegment" in js, "findNearestSegment not found")

check("HV-505", "projectToScreen 関数が存在",
      "projectToScreen" in js, "projectToScreen not found")

check("HV-506", "distPointToSegment2D 関数が存在",
      "distPointToSegment2D" in js, "distPointToSegment2D not found")

check("HV-507", "15px 閾値が設定されている",
      "< 15" in js or "<15" in js or "<= 15" in js,
      "15px threshold not found")

check("HV-508", "degree==2 判定による探索停止",
      "!== 2" in js or "!= 2" in js,
      "degree!=2 check not found")

check("HV-509", "highlightSet によるハイライト管理",
      "highlightSet" in js, "highlightSet not found")

check("HV-510", "tooltip 要素の使用",
      "tooltip" in js, "tooltip not found")

check("HV-511", "「(名称不明)」フォールバック表示",
      "(名称不明)" in js, "(名称不明) fallback not found")

check("HV-512", "ドラッグ中はホバーをスキップ",
      "dragging" in js and "rightDrag" in js,
      "drag check not found")

check("HV-513", "mouseleave でハイライト解除",
      "mouseleave" in js, "mouseleave handler not found")

# ========================================
# HV-6xx: 仕様書の記載確認
# ========================================
print("[HV-6] spec-preview.md の記載確認")

check("HV-601", "仕様書にホバー・ハイライトセクションが存在",
      "マウスホバー" in spec or "ホバー" in spec,
      "hover section not found in spec")

check("HV-602", "仕様書に隣接グラフの記載",
      "隣接" in spec, "adjacency graph not in spec")

check("HV-603", "仕様書にフラッドフィルの記載",
      "フラッドフィル" in spec, "flood fill not in spec")

check("HV-604", "仕様書にdegree!=2 の停止条件",
      "degree!=2" in spec or "degree==2" in spec,
      "degree stop condition not in spec")

check("HV-605", "仕様書に15px 閾値の記載",
      "15px" in spec, "15px threshold not in spec")

check("HV-606", "仕様書にツールチップの記載",
      "ツールチップ" in spec or "tooltip" in spec,
      "tooltip not in spec")

# ========================================
# サマリー
# ========================================
print()
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)
