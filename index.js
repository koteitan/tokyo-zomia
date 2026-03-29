// 河川水系 + 海岸線 3D Preview
(async function () {
  /**
   * gzip圧縮されたJSONファイルをfetchし、DecompressionStreamで解凍してパースする。
   */
  async function fetchGzJson(url) {
    const resp = await fetch(url);
    const ds = new DecompressionStream("gzip");
    const decompressedStream = resp.body.pipeThrough(ds);
    const reader = decompressedStream.getReader();
    const chunks = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    const blob = new Blob(chunks);
    const text = await blob.text();
    return JSON.parse(text);
  }

  const [riversGJ, coastGJ] = await Promise.all([
    fetchGzJson("data/rivers.geojson.gz"),
    fetchGzJson("data/coastline.geojson.gz"),
  ]);

  // GeoJSON → 内部形式に変換
  const segments = riversGJ.features.map((f) => ({
    coordinates: f.geometry.coordinates,
    properties: f.properties,
  }));
  const coastlines = coastGJ.features.map((f) => ({
    coordinates: f.geometry.coordinates,
    is_river_mouth: f.properties.is_river_mouth,
  }));

  // --- 隣接グラフ構築 (start_node/end_node) ---
  const nodeToSegs = {};  // nodeId -> [segIndex, ...]
  const nodeDegree = {};  // nodeId -> degree
  for (let i = 0; i < segments.length; i++) {
    const p = segments[i].properties;
    const sn = p.start_node;
    const en = p.end_node;
    if (sn) { (nodeToSegs[sn] = nodeToSegs[sn] || []).push(i); nodeDegree[sn] = (nodeDegree[sn] || 0) + 1; }
    if (en) { (nodeToSegs[en] = nodeToSegs[en] || []).push(i); nodeDegree[en] = (nodeDegree[en] || 0) + 1; }
  }

  // ハイライト対象セグメントのインデックス集合
  let highlightSet = new Set();
  let hoveredRiverName = "";

  // --- データ前処理: 全データの範囲を統合して正規化 ---
  let lonMin = Infinity, lonMax = -Infinity;
  let latMin = Infinity, latMax = -Infinity;
  let elevMin = Infinity, elevMax = -Infinity;

  for (const seg of segments) {
    for (const p of seg.coordinates) {
      if (p[0] < lonMin) lonMin = p[0];
      if (p[0] > lonMax) lonMax = p[0];
      if (p[1] < latMin) latMin = p[1];
      if (p[1] > latMax) latMax = p[1];
      if (p[2] < elevMin) elevMin = p[2];
      if (p[2] > elevMax) elevMax = p[2];
    }
  }
  for (const seg of coastlines) {
    for (const p of seg.coordinates) {
      if (p[0] < lonMin) lonMin = p[0];
      if (p[0] > lonMax) lonMax = p[0];
      if (p[1] < latMin) latMin = p[1];
      if (p[1] > latMax) latMax = p[1];
    }
  }

  const centerLat = (latMin + latMax) / 2;
  const mPerDegLon = 111320 * Math.cos((centerLat * Math.PI) / 180);
  const mPerDegLat = 110540;

  const rangeX = (lonMax - lonMin) * mPerDegLon;
  const rangeY = (latMax - latMin) * mPerDegLat;
  const rangeMax = Math.max(rangeX, rangeY);

  const lonCenter = (lonMin + lonMax) / 2;
  const latCenter = (latMin + latMax) / 2;

  let elevScale = 10;

  function normalize(lon, lat, elev) {
    const x = ((lon - lonCenter) * mPerDegLon) / rangeMax;
    const z = -((lat - latCenter) * mPerDegLat) / rangeMax;
    const y = ((elev - elevMin) / rangeMax) * elevScale;
    return [x, y, z];
  }

  function elevColor(elev) {
    const t = (elev - elevMin) / (elevMax - elevMin || 1);
    let r, g, b;
    if (t < 0.33) {
      const s = t / 0.33;
      r = 0; g = s; b = 1 - s;
    } else if (t < 0.66) {
      const s = (t - 0.33) / 0.33;
      r = s; g = 1; b = 0;
    } else {
      const s = (t - 0.66) / 0.34;
      r = 1; g = 1 - s; b = 0;
    }
    return [r, g, b];
  }

  // --- Canvas/GL ---
  const canvas = document.getElementById("c");
  const gl = canvas.getContext("webgl", { antialias: true });

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  window.addEventListener("resize", resize);

  // --- シェーダー ---
  const vsrc = `
    attribute vec3 aPos;
    attribute vec3 aColor;
    uniform mat4 uMVP;
    uniform float uPointSize;
    varying vec3 vColor;
    void main() {
      vColor = aColor;
      gl_Position = uMVP * vec4(aPos, 1.0);
      gl_PointSize = uPointSize;
    }
  `;
  const fsrc = `
    precision mediump float;
    varying vec3 vColor;
    void main() {
      gl_FragColor = vec4(vColor, 1.0);
    }
  `;

  function compileShader(src, type) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, compileShader(vsrc, gl.VERTEX_SHADER));
  gl.attachShader(prog, compileShader(fsrc, gl.FRAGMENT_SHADER));
  gl.linkProgram(prog);
  gl.useProgram(prog);

  const aPos = gl.getAttribLocation(prog, "aPos");
  const aColor = gl.getAttribLocation(prog, "aColor");
  const uMVP = gl.getUniformLocation(prog, "uMVP");
  const uPointSize = gl.getUniformLocation(prog, "uPointSize");

  // --- 河川ジオメトリ ---
  let lineBuf, lineColorBuf, lineVertCount;
  let nodeBuf, nodeColorBuf, nodeCount;

  // --- 海岸線ジオメトリ ---
  let coastBuf, coastColorBuf, coastVertCount;

  function buildRiverGeometry() {
    const verts = [];
    const colors = [];
    for (let si = 0; si < segments.length; si++) {
      const seg = segments[si];
      const hl = highlightSet.has(si);
      const coords = seg.coordinates;
      for (let i = 0; i < coords.length - 1; i++) {
        const p0 = normalize(coords[i][0], coords[i][1], coords[i][2]);
        const p1 = normalize(coords[i + 1][0], coords[i + 1][1], coords[i + 1][2]);
        if (hl) {
          colors.push(1, 1, 1, 1, 1, 1);
        } else {
          const c0 = elevColor(coords[i][2]);
          const c1 = elevColor(coords[i + 1][2]);
          colors.push(...c0, ...c1);
        }
        verts.push(...p0, ...p1);
      }
    }
    lineVertCount = verts.length / 3;

    if (!lineBuf) lineBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, lineBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.DYNAMIC_DRAW);

    if (!lineColorBuf) lineColorBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, lineColorBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);

    // 端点
    const nv = [];
    const nc = [];
    const seen = new Set();
    for (const seg of segments) {
      const coords = seg.coordinates;
      for (const idx of [0, coords.length - 1]) {
        const c = coords[idx];
        const key = `${c[0]},${c[1]}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const p = normalize(c[0], c[1], c[2]);
        nv.push(...p);
        nc.push(1, 1, 1);
      }
    }
    nodeCount = nv.length / 3;

    if (!nodeBuf) nodeBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, nodeBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(nv), gl.DYNAMIC_DRAW);

    if (!nodeColorBuf) nodeColorBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, nodeColorBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(nc), gl.STATIC_DRAW);
  }

  function buildCoastGeometry() {
    const verts = [];
    const colors = [];
    for (const seg of coastlines) {
      const coords = seg.coordinates;
      for (let i = 0; i < coords.length - 1; i++) {
        const p0 = normalize(coords[i][0], coords[i][1], 0);
        const p1 = normalize(coords[i + 1][0], coords[i + 1][1], 0);
        verts.push(...p0, ...p1);
        // 海岸線は水色、河口は黄色
        if (seg.is_river_mouth) {
          colors.push(1, 1, 0.3, 1, 1, 0.3);
        } else {
          colors.push(0.3, 0.6, 0.8, 0.3, 0.6, 0.8);
        }
      }
    }
    coastVertCount = verts.length / 3;

    if (!coastBuf) coastBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, coastBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.DYNAMIC_DRAW);

    if (!coastColorBuf) coastColorBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, coastColorBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
  }

  function rebuildAll() {
    buildRiverGeometry();
    buildCoastGeometry();
  }

  rebuildAll();

  // --- 行列ユーティリティ ---
  function mat4Ident() {
    return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
  }
  function mat4Mult(a, b) {
    const r = new Float32Array(16);
    for (let i = 0; i < 4; i++)
      for (let j = 0; j < 4; j++)
        for (let k = 0; k < 4; k++)
          r[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k];
    return r;
  }
  function mat4Perspective(fov, aspect, near, far) {
    const f = 1 / Math.tan(fov / 2);
    const nf = 1 / (near - far);
    return new Float32Array([
      f/aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far+near)*nf, -1,
      0, 0, 2*far*near*nf, 0
    ]);
  }
  function mat4Translate(x, y, z) {
    const m = mat4Ident();
    m[12] = x; m[13] = y; m[14] = z;
    return m;
  }
  function mat4RotX(a) {
    const m = mat4Ident();
    m[5] = Math.cos(a); m[6] = Math.sin(a);
    m[9] = -Math.sin(a); m[10] = Math.cos(a);
    return m;
  }
  function mat4RotY(a) {
    const m = mat4Ident();
    m[0] = Math.cos(a); m[2] = -Math.sin(a);
    m[8] = Math.sin(a); m[10] = Math.cos(a);
    return m;
  }

  // --- カメラ ---
  let rotX = -Math.PI / 2, rotY = 0, zoom = 2.5, panX = 0, panY = 0;

  function getMVP() {
    const aspect = canvas.width / canvas.height;
    const proj = mat4Perspective(Math.PI / 4, aspect, 0.01, 100);
    let view = mat4Translate(panX, panY, -zoom);
    view = mat4Mult(view, mat4RotX(rotX));
    view = mat4Mult(view, mat4RotY(rotY));
    return mat4Mult(proj, view);
  }

  // --- 3D→スクリーン投影 ---
  function projectToScreen(wx, wy, wz, mvp) {
    const x = mvp[0]*wx + mvp[4]*wy + mvp[8]*wz + mvp[12];
    const y = mvp[1]*wx + mvp[5]*wy + mvp[9]*wz + mvp[13];
    const w = mvp[3]*wx + mvp[7]*wy + mvp[11]*wz + mvp[15];
    if (w <= 0) return null;
    const ndcX = x / w, ndcY = y / w;
    return [(ndcX * 0.5 + 0.5) * canvas.width, (1 - (ndcY * 0.5 + 0.5)) * canvas.height];
  }

  // 点からスクリーン空間の線分への距離
  function distPointToSegment2D(px, py, ax, ay, bx, by) {
    const dx = bx - ax, dy = by - ay;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.sqrt((px - ax) ** 2 + (py - ay) ** 2);
    let t = ((px - ax) * dx + (py - ay) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    const cx = ax + t * dx, cy = ay + t * dy;
    return Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
  }

  // 最近傍セグメント検索
  function findNearestSegment(mx, my, mvp) {
    let bestDist = Infinity, bestIdx = -1;
    for (let i = 0; i < segments.length; i++) {
      const coords = segments[i].coordinates;
      for (let j = 0; j < coords.length - 1; j++) {
        const p0 = normalize(coords[j][0], coords[j][1], coords[j][2]);
        const p1 = normalize(coords[j + 1][0], coords[j + 1][1], coords[j + 1][2]);
        const s0 = projectToScreen(p0[0], p0[1], p0[2], mvp);
        const s1 = projectToScreen(p1[0], p1[1], p1[2], mvp);
        if (!s0 || !s1) continue;
        const d = distPointToSegment2D(mx, my, s0[0], s0[1], s1[0], s1[1]);
        if (d < bestDist) { bestDist = d; bestIdx = i; }
      }
    }
    return bestDist < 15 ? bestIdx : -1; // 15px 閾値
  }

  // 分岐・合流点 (degree!=2) までフラッドフィル
  function floodFillSegments(startIdx) {
    const result = new Set([startIdx]);
    const queue = [startIdx];
    while (queue.length > 0) {
      const idx = queue.pop();
      const p = segments[idx].properties;
      for (const nodeId of [p.start_node, p.end_node]) {
        if (!nodeId || nodeDegree[nodeId] !== 2) continue;
        for (const neighbor of (nodeToSegs[nodeId] || [])) {
          if (!result.has(neighbor)) {
            result.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }
    return result;
  }

  // --- マウス操作 ---
  let dragging = false, rightDrag = false, lastX, lastY;
  let mouseX = 0, mouseY = 0;
  const tooltip = document.getElementById("tooltip");

  canvas.addEventListener("mousedown", (e) => {
    if (e.button === 2) { rightDrag = true; } else { dragging = true; }
    lastX = e.clientX; lastY = e.clientY;
  });
  canvas.addEventListener("mousemove", (e) => {
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    if (dragging) {
      rotY += dx * 0.005;
      rotX += dy * 0.005;
      rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
    }
    if (rightDrag) {
      panX += dx * 0.002 * zoom;
      panY -= dy * 0.002 * zoom;
    }
    lastX = e.clientX; lastY = e.clientY;
    mouseX = e.clientX; mouseY = e.clientY;

    // ホバー判定（ドラッグ中はスキップ）
    if (!dragging && !rightDrag) {
      const mvp = getMVP();
      const idx = findNearestSegment(mouseX, mouseY, mvp);
      if (idx >= 0) {
        highlightSet = floodFillSegments(idx);
        hoveredRiverName = segments[idx].properties.river_name || "";
        tooltip.style.display = "block";
        tooltip.style.left = (mouseX + 12) + "px";
        tooltip.style.top = (mouseY + 12) + "px";
        tooltip.textContent = hoveredRiverName || "(名称不明)";
        highlightDirty = true;
      } else if (highlightSet.size > 0) {
        highlightSet = new Set();
        hoveredRiverName = "";
        tooltip.style.display = "none";
        highlightDirty = true;
      }
    }
  });
  canvas.addEventListener("mouseup", () => { dragging = false; rightDrag = false; });
  canvas.addEventListener("mouseleave", () => {
    if (highlightSet.size > 0) {
      highlightSet = new Set();
      hoveredRiverName = "";
      tooltip.style.display = "none";
      highlightDirty = true;
    }
  });
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  canvas.addEventListener("wheel", (e) => {
    zoom *= e.deltaY > 0 ? 1.1 : 0.9;
    zoom = Math.max(0.1, Math.min(20, zoom));
    e.preventDefault();
  });

  // --- UI ---
  const elevSlider = document.getElementById("elevScale");
  const elevVal = document.getElementById("elevScaleVal");
  const showNodesCheck = document.getElementById("showNodes");
  const showCoastCheck = document.getElementById("showCoast");

  elevSlider.addEventListener("input", () => {
    elevScale = Number(elevSlider.value);
    elevVal.textContent = elevScale;
    rebuildAll();
  });

  // --- グリッド ---
  function buildGrid() {
    const v = [];
    const c = [];
    const n = 10;
    for (let i = -n; i <= n; i++) {
      const t = i / n * 0.8;
      v.push(t, 0, -0.8, t, 0, 0.8);
      v.push(-0.8, 0, t, 0.8, 0, t);
      c.push(0.2, 0.2, 0.2, 0.2, 0.2, 0.2);
      c.push(0.2, 0.2, 0.2, 0.2, 0.2, 0.2);
    }
    const gridBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, gridBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(v), gl.STATIC_DRAW);
    const gridColorBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, gridColorBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(c), gl.STATIC_DRAW);
    return { buf: gridBuf, colorBuf: gridColorBuf, count: v.length / 3 };
  }
  const grid = buildGrid();

  // --- 描画ループ ---
  gl.enable(gl.DEPTH_TEST);
  gl.clearColor(0.08, 0.08, 0.12, 1);

  let highlightDirty = false;

  function draw() {
    // ハイライト変更時のみ河川カラーバッファを更新
    if (highlightDirty) {
      buildRiverGeometry();
      highlightDirty = false;
    }

    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const mvp = getMVP();
    gl.uniformMatrix4fv(uMVP, false, mvp);

    // グリッド
    gl.uniform1f(uPointSize, 1.0);
    gl.bindBuffer(gl.ARRAY_BUFFER, grid.buf);
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, grid.colorBuf);
    gl.enableVertexAttribArray(aColor);
    gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.LINES, 0, grid.count);

    // 海岸線
    if (showCoastCheck.checked) {
      gl.bindBuffer(gl.ARRAY_BUFFER, coastBuf);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, coastColorBuf);
      gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.LINES, 0, coastVertCount);
    }

    // 河川ライン
    gl.bindBuffer(gl.ARRAY_BUFFER, lineBuf);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, lineColorBuf);
    gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.LINES, 0, lineVertCount);

    // 端点
    if (showNodesCheck.checked) {
      gl.uniform1f(uPointSize, 4.0);
      gl.bindBuffer(gl.ARRAY_BUFFER, nodeBuf);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, nodeColorBuf);
      gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.POINTS, 0, nodeCount);
    }

    requestAnimationFrame(draw);
  }
  draw();
})();
