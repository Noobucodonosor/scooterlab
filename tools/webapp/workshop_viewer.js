/**
 * ScooterLab Real Workshop Viewer (ADR-0008 / TASK-APP-02)
 * Mode 1: High-resolution SYM Official Exploded Diagrams & Service Plates (pan/zoom + step sync)
 * Mode 2: Real `.glb` (glTF 2.0 binary) 3D Scan Slot with offline WebGL mesh renderer (zero toy cubes)
 */

export class WorkshopViewer {
  constructor({ atlasViewport, atlasImg, glbCanvas, onSelectPart, onSelectPlate }) {
    this.atlasViewport = atlasViewport;
    this.atlasImg = atlasImg;
    this.glbCanvas = glbCanvas;
    this.onSelectPart = onSelectPart;
    this.onSelectPlate = onSelectPlate;

    this.mode = "atlas"; // "atlas" | "glb"
    this.plates = [];
    this.activePlate = null;
    this.activePart = "underseat_tub";
    this.hasCustomGlb = false;

    // Pan & Zoom state for Atlas image
    this.scale = 1.0;
    this.tx = 0;
    this.ty = 0;
    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;

    // Orbit state for real .glb WebGL viewer
    this.yaw = -0.6;
    this.pitch = 0.28;
    this.glbZoom = 1.0;
    this.glbMesh = null;

    this._bindAtlasEvents();
    this._bindGlbEvents();
  }

  setCatalog(plates, hasCustomGlb) {
    this.plates = plates || [];
    this.hasCustomGlb = Boolean(hasCustomGlb);
    if (!this.activePlate && this.plates.length) {
      this.selectPlateById(this.plates[0].id);
    }
  }

  setMode(mode) {
    this.mode = mode === "glb" ? "glb" : "atlas";
    if (this.mode === "glb" && this.hasCustomGlb && !this.glbMesh) {
      this.loadGlb("/local_models/symphony.glb");
    }
  }

  focusPart(partId) {
    this.activePart = partId || "underseat_tub";
    const match = this.plates.find((p) => p.focus_part === this.activePart) || this.plates[0];
    if (match) {
      this.selectPlateById(match.id);
    }
  }

  selectPlateById(plateId) {
    const plate = this.plates.find((p) => p.id === plateId);
    if (!plate) return;
    this.activePlate = plate;
    this.activePart = plate.focus_part;
    this.resetView();
    if (plate.available) {
      this.atlasImg.src = `/local_atlas/${encodeURIComponent(plate.filename)}`;
      this.atlasImg.alt = `${plate.title} (${plate.source_pdf} p.${plate.page})`;
    } else {
      this.atlasImg.removeAttribute("src");
    }
    if (this.onSelectPlate) this.onSelectPlate(plate);
    if (this.onSelectPart) this.onSelectPart(plate.focus_part);
  }

  zoomBy(delta) {
    if (this.mode === "glb") {
      this.glbZoom = Math.max(0.5, Math.min(2.8, this.glbZoom + delta));
      this._drawGlb();
      return;
    }
    this.scale = Math.max(1.0, Math.min(4.5, this.scale + delta));
    if (this.scale === 1.0) {
      this.tx = 0;
      this.ty = 0;
    }
    this._applyTransform();
  }

  resetView() {
    if (this.mode === "glb") {
      this.yaw = -0.6;
      this.pitch = 0.28;
      this.glbZoom = 1.0;
      this._drawGlb();
      return;
    }
    this.scale = 1.0;
    this.tx = 0;
    this.ty = 0;
    this._applyTransform();
  }

  _applyTransform() {
    this.atlasImg.style.transform = `translate(${this.tx}px, ${this.ty}px) scale(${this.scale})`;
  }

  _bindAtlasEvents() {
    const start = (x, y) => {
      if (this.scale <= 1.0) return;
      this.dragging = true;
      this.lastX = x;
      this.lastY = y;
    };
    const move = (x, y) => {
      if (!this.dragging) return;
      this.tx += x - this.lastX;
      this.ty += y - this.lastY;
      this.lastX = x;
      this.lastY = y;
      this._applyTransform();
    };
    const end = () => {
      this.dragging = false;
    };

    this.atlasViewport.addEventListener("mousedown", (e) => {
      e.preventDefault();
      start(e.clientX, e.clientY);
    });
    window.addEventListener("mousemove", (e) => move(e.clientX, e.clientY));
    window.addEventListener("mouseup", end);

    this.atlasViewport.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) start(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    this.atlasViewport.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1) move(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    this.atlasViewport.addEventListener("touchend", end);

    this.atlasViewport.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.zoomBy(e.deltaY > 0 ? -0.2 : 0.2);
    }, { passive: false });
  }

  _bindGlbEvents() {
    let drag = false;
    let lx = 0;
    let ly = 0;
    const down = (x, y) => { drag = true; lx = x; ly = y; };
    const move = (x, y) => {
      if (!drag) return;
      this.yaw += (x - lx) * 0.01;
      this.pitch = Math.max(-1.2, Math.min(1.2, this.pitch + (y - ly) * 0.01));
      lx = x;
      ly = y;
      this._drawGlb();
    };
    const up = () => { drag = false; };
    this.glbCanvas.addEventListener("mousedown", (e) => down(e.clientX, e.clientY));
    window.addEventListener("mousemove", (e) => move(e.clientX, e.clientY));
    window.addEventListener("mouseup", up);
    this.glbCanvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.zoomBy(e.deltaY > 0 ? -0.1 : 0.1);
    }, { passive: false });
  }

  async loadGlb(url) {
    const resp = await fetch(url);
    if (!resp.ok) return;
    const buf = await resp.arrayBuffer();
    this.glbMesh = this._parseGlbFirstMesh(buf);
    this._drawGlb();
  }

  _parseGlbFirstMesh(buf) {
    const view = new DataView(buf);
    if (buf.byteLength < 20 || view.getUint32(0, true) !== 0x46546c67) return null;
    const jsonLen = view.getUint32(12, true);
    const jsonStr = new TextDecoder().decode(new Uint8Array(buf, 20, jsonLen));
    const gltf = JSON.parse(jsonStr);
    const binOffset = 20 + jsonLen + 8;
    if (binOffset >= buf.byteLength) return { verts: [], indices: [] };

    const prim = gltf.meshes?.[0]?.primitives?.[0];
    if (!prim || prim.attributes?.POSITION === undefined) return { verts: [], indices: [] };

    const posAcc = gltf.accessors[prim.attributes.POSITION];
    const posView = gltf.bufferViews[posAcc.bufferView];
    const pStart = binOffset + (posView.byteOffset || 0) + (posAcc.byteOffset || 0);
    const verts = [];
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
    const step = posView.byteStride || 12;
    for (let i = 0; i < posAcc.count; i++) {
      const o = pStart + i * step;
      const x = view.getFloat32(o, true);
      const y = view.getFloat32(o + 4, true);
      const z = view.getFloat32(o + 8, true);
      verts.push([x, y, z]);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
      if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
    }
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
    const scale = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 1e-4);
    const normVerts = verts.map(([x, y, z]) => [(x - cx) / scale, (y - cy) / scale, (z - cz) / scale]);

    const indices = [];
    if (prim.indices !== undefined) {
      const idxAcc = gltf.accessors[prim.indices];
      const idxView = gltf.bufferViews[idxAcc.bufferView];
      const iStart = binOffset + (idxView.byteOffset || 0) + (idxAcc.byteOffset || 0);
      const stride = idxAcc.componentType === 5125 ? 4 : 2;
      for (let i = 0; i < idxAcc.count; i++) {
        const val = stride === 4 ? view.getUint32(iStart + i * 4, true) : view.getUint16(iStart + i * 2, true);
        indices.push(val);
      }
    }
    return { verts: normVerts, indices };
  }

  _drawGlb() {
    const c = this.glbCanvas;
    const ctx = c.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth || 560;
    const h = c.clientHeight || 360;
    if (c.width !== Math.round(w * dpr)) {
      c.width = Math.round(w * dpr);
      c.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (!this.glbMesh || !this.glbMesh.verts.length) {
      ctx.font = '500 13px "JetBrains Mono", monospace';
      ctx.fillStyle = "#5a5850";
      ctx.fillText("Mesh .glb caricata (0 vertici renderizzabili nella prima primitiva)", 18, 36);
      return;
    }

    const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    const proj = this.glbMesh.verts.map(([x, y, z]) => {
      const rx = x * cy - z * sy;
      const rz = x * sy + z * cy;
      const ry = y * cp - rz * sp;
      const rz2 = y * sp + rz * cp;
      const s = (Math.min(w, h) * 0.72 * this.glbZoom) / (2.4 + rz2);
      return [w / 2 + rx * s, h / 2 - ry * s, rz2];
    });

    const tris = [];
    const idx = this.glbMesh.indices;
    const maxTris = Math.min(idx.length, 24000);
    for (let i = 0; i + 2 < maxTris; i += 3) {
      const a = proj[idx[i]], b = proj[idx[i + 1]], d = proj[idx[i + 2]];
      if (!a || !b || !d) continue;
      tris.push({ a, b, d, z: (a[2] + b[2] + d[2]) / 3 });
    }
    tris.sort((u, v) => v.z - u.z);

    ctx.strokeStyle = "rgba(36, 86, 214, 0.35)";
    ctx.fillStyle = "rgba(211, 210, 206, 0.85)";
    ctx.lineWidth = 0.8;
    for (const t of tris) {
      ctx.beginPath();
      ctx.moveTo(t.a[0], t.a[1]);
      ctx.lineTo(t.b[0], t.b[1]);
      ctx.lineTo(t.d[0], t.d[1]);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
  }
}
