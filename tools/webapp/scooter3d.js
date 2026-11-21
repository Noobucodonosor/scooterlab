/**
 * ScooterLab Offline Parametric 3D Digital Twin — SYM Symphony ST 200i ABS
 * Built from verified proportions: length 2000mm, wheelbase 1350mm, 16" wheels, seat 792mm.
 * Zero external dependencies / WebGL fallbacks: works offline in any garage browser.
 */

export class Scooter3DViewer {
  constructor(canvas, onPartSelect) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onPartSelect = onPartSelect;

    this.yaw = -0.68;
    this.pitch = 0.24;
    this.zoom = 1.0;
    this.xray = true;
    this.activePart = "scooterlab_box";

    this.targetYaw = this.yaw;
    this.targetPitch = this.pitch;
    this.targetZoom = this.zoom;

    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;
    this.hotspots = [];

    this._initParts();
    this._bindEvents();
    this._loop();
  }

  _initParts() {
    // Coordinate system (normalized meters, origin at center floorboard):
    // X: rear(-1.0) -> front(+1.0), Y: down(-) -> up(+), Z: left(-) -> right(+)
    this.partsMeta = {
      wheels_abs: {
        label: "Ruote 16\" & Anelli ABS (50 fori)",
        view: { yaw: -0.95, pitch: 0.16, zoom: 1.05 },
        center: [0.68, -0.35, 0.0],
      },
      front_obd: {
        label: "Scudo, Cruscotto & OBD/CAN (Liv. C)",
        view: { yaw: 0.62, pitch: 0.25, zoom: 1.18 },
        center: [0.56, 0.28, 0.0],
      },
      underseat_tub: {
        label: "Cestello Sottosella (Liv. A)",
        view: { yaw: -0.55, pitch: 0.48, zoom: 1.25 },
        center: [-0.26, 0.22, 0.0],
      },
      battery_fuses: {
        label: "Batteria 12V 6Ah & Fusibili",
        view: { yaw: -0.45, pitch: 0.36, zoom: 1.35 },
        center: [-0.14, 0.06, 0.0],
      },
      scooterlab_box: {
        label: "Centralina ScooterLab IP65",
        view: { yaw: 0.42, pitch: 0.42, zoom: 1.38 },
        center: [-0.02, 0.16, 0.0],
      },
      engine_valves: {
        label: "Motore 169cc, Candela & Valvole",
        view: { yaw: 1.15, pitch: 0.15, zoom: 1.32 },
        center: [-0.42, -0.14, 0.12],
      },
      cvt_case: {
        label: "Carter CVT, Rulli 18×14 & Filtro Aria",
        view: { yaw: -1.42, pitch: 0.14, zoom: 1.32 },
        center: [-0.52, -0.22, -0.18],
      },
    };

    const wheelBoxes = (cx, cy, cz, r, w) => {
      const boxes = [];
      const segs = 12;
      for (let i = 0; i < segs; i++) {
        const a0 = (i / segs) * Math.PI * 2;
        const a1 = ((i + 1) / segs) * Math.PI * 2;
        const x0 = cx + Math.cos(a0) * r;
        const y0 = cy + Math.sin(a0) * r;
        const x1 = cx + Math.cos(a1) * r;
        const y1 = cy + Math.sin(a1) * r;
        boxes.push({
          part: "wheels_abs",
          shell: false,
          verts: [
            [x0, y0, cz - w / 2],
            [x1, y1, cz - w / 2],
            [x1, y1, cz + w / 2],
            [x0, y0, cz + w / 2],
          ],
          fill: "rgba(38,37,30,0.72)",
          stroke: "#26251e",
        });
      }
      // ABS 50-hole tone ring accent
      boxes.push(...this._makeBox([cx, cy, cz + w * 0.6], [0.16, 0.16, 0.02], "wheels_abs", false, "rgba(36,86,214,0.35)"));
      return boxes;
    };

    this.faces = [
      // Wheels (wheelbase 1.35m -> front +0.675, rear -0.675; 16" wheel ~0.28m radius)
      ...wheelBoxes(0.675, -0.34, 0, 0.26, 0.11),
      ...wheelBoxes(-0.675, -0.34, 0, 0.26, 0.12),

      // Flat floorboard & frame spine (shell)
      ...this._makeBox([0.08, -0.14, 0], [0.68, 0.08, 0.36], "underseat_tub", true),
      // Rear body panels & seat (seat height ~792mm above ground)
      ...this._makeBox([-0.36, 0.16, 0], [0.74, 0.32, 0.36], "underseat_tub", true),
      ...this._makeBox([-0.32, 0.35, 0], [0.64, 0.09, 0.30], "underseat_tub", true),
      // Rear carrier rack
      ...this._makeBox([-0.82, 0.34, 0], [0.22, 0.04, 0.24], "underseat_tub", true),

      // Front shield, steering column & handlebar (Livello C)
      ...this._makeBox([0.52, 0.18, 0], [0.26, 0.56, 0.34], "front_obd", true),
      ...this._makeBox([0.46, 0.54, 0], [0.14, 0.12, 0.64], "front_obd", false),
      ...this._makeBox([0.56, 0.22, 0], [0.09, 0.12, 0.14], "front_obd", false),

      // Internal: Battery 12V 6Ah + Fuse box
      ...this._makeBox([-0.14, 0.05, 0.02], [0.15, 0.12, 0.11], "battery_fuses", false),

      // Internal: ScooterLab Rev. 2 IP65 enclosure (forward underseat bay)
      ...this._makeBox([-0.02, 0.17, -0.02], [0.12, 0.07, 0.09], "scooterlab_box", false),

      // Engine 169cc cylinder + head + spark plug (right/center)
      ...this._makeBox([-0.40, -0.14, 0.06], [0.28, 0.22, 0.20], "engine_valves", false),

      // CVT transmission case & airbox (left side Z < 0)
      ...this._makeBox([-0.52, -0.22, -0.17], [0.54, 0.19, 0.10], "cvt_case", false),
      ...this._makeBox([-0.56, -0.04, -0.17], [0.26, 0.12, 0.10], "cvt_case", false),
    ];
  }

  _makeBox(center, size, part, isShell, customFill = null) {
    const [cx, cy, cz] = center;
    const [hx, hy, hz] = [size[0] / 2, size[1] / 2, size[2] / 2];
    const v = [
      [cx - hx, cy - hy, cz - hz],
      [cx + hx, cy - hy, cz - hz],
      [cx + hx, cy + hy, cz - hz],
      [cx - hx, cy + hy, cz - hz],
      [cx - hx, cy - hy, cz + hz],
      [cx + hx, cy - hy, cz + hz],
      [cx + hx, cy + hy, cz + hz],
      [cx - hx, cy + hy, cz + hz],
    ];
    const quads = [
      [0, 1, 2, 3],
      [4, 5, 6, 7],
      [0, 1, 5, 4],
      [2, 3, 7, 6],
      [1, 2, 6, 5],
      [0, 3, 7, 4],
    ];
    return quads.map((q) => ({
      part,
      shell: isShell,
      verts: q.map((idx) => v[idx]),
      fill: customFill,
      stroke: null,
    }));
  }

  setXRay(enabled) {
    this.xray = Boolean(enabled);
  }

  zoomBy(delta) {
    this.targetZoom = Math.max(0.7, Math.min(2.1, this.targetZoom + delta));
  }

  resetView() {
    this.targetYaw = -0.68;
    this.targetPitch = 0.24;
    this.targetZoom = 1.0;
  }

  focusPart(partId) {
    if (!this.partsMeta[partId]) return;
    this.activePart = partId;
    const v = this.partsMeta[partId].view;
    this.targetYaw = v.yaw;
    this.targetPitch = v.pitch;
    this.targetZoom = v.zoom;
  }

  _bindEvents() {
    const down = (x, y) => {
      this.dragging = true;
      this.lastX = x;
      this.lastY = y;
      this._dragDist = 0;
    };
    const move = (x, y) => {
      if (!this.dragging) return;
      const dx = x - this.lastX;
      const dy = y - this.lastY;
      this._dragDist += Math.hypot(dx, dy);
      this.lastX = x;
      this.lastY = y;
      this.targetYaw += dx * 0.01;
      this.targetPitch = Math.max(-0.55, Math.min(1.05, this.targetPitch + dy * 0.01));
    };
    const up = (x, y) => {
      if (!this.dragging) return;
      this.dragging = false;
      if (this._dragDist < 6) {
        this._handleClick(x, y);
      }
    };

    this.canvas.addEventListener("mousedown", (e) => down(e.clientX, e.clientY));
    window.addEventListener("mousemove", (e) => move(e.clientX, e.clientY));
    window.addEventListener("mouseup", (e) => up(e.clientX, e.clientY));

    this.canvas.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) down(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    this.canvas.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1) move(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    this.canvas.addEventListener("touchend", (e) => {
      if (e.changedTouches.length === 1) up(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.zoomBy(e.deltaY > 0 ? -0.08 : 0.08);
    }, { passive: false });
  }

  _handleClick(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    let best = null;
    let bestD = 26;
    for (const h of this.hotspots) {
      const d = Math.hypot(px - h.x, py - h.y);
      if (d < bestD) {
        bestD = d;
        best = h.id;
      }
    }
    if (best) {
      this.focusPart(best);
      if (this.onPartSelect) this.onPartSelect(best);
    }
  }

  _project([x, y, z], w, h) {
    const cy = Math.cos(this.yaw);
    const sy = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);

    const rx = x * cy - z * sy;
    const rz = x * sy + z * cy;
    const ry = y * cp - rz * sp;
    const rz2 = y * sp + rz * cp;

    const camDist = 3.2;
    const scale = (Math.min(w, h) * 0.85 * this.zoom) / (camDist + rz2);
    return {
      x: w / 2 + rx * scale,
      y: h / 2 - ry * scale,
      depth: rz2,
    };
  }

  _draw() {
    const dpr = window.devicePixelRatio || 1;
    const w = this.canvas.clientWidth || 600;
    const h = this.canvas.clientHeight || 360;
    if (this.canvas.width !== Math.round(w * dpr) || this.canvas.height !== Math.round(h * dpr)) {
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
    }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // Subtle blueprint grid floor
    ctx.strokeStyle = "rgba(36, 86, 214, 0.10)";
    ctx.lineWidth = 1;
    for (let gx = -1.2; gx <= 1.21; gx += 0.3) {
      const a = this._project([gx, -0.60, -0.6], w, h);
      const b = this._project([gx, -0.60, 0.6], w, h);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    const projected = this.faces.map((face) => {
      const pts = face.verts.map((v) => this._project(v, w, h));
      const avgDepth = pts.reduce((acc, p) => acc + p.depth, 0) / pts.length;
      return { face, pts, avgDepth };
    });

    projected.sort((a, b) => b.avgDepth - a.avgDepth);

    for (const item of projected) {
      const { face, pts } = item;
      const isSelected = face.part === this.activePart;
      ctx.beginPath();
      pts.forEach((p, idx) => (idx === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
      ctx.closePath();

      if (face.fill) {
        ctx.fillStyle = face.fill;
      } else if (isSelected) {
        ctx.fillStyle = face.shell && this.xray ? "rgba(36, 86, 214, 0.18)" : "rgba(36, 86, 214, 0.42)";
      } else if (face.shell) {
        ctx.fillStyle = this.xray ? "rgba(211, 210, 206, 0.16)" : "rgba(211, 210, 206, 0.78)";
      } else {
        ctx.fillStyle = "rgba(90, 88, 80, 0.35)";
      }
      ctx.fill();

      ctx.strokeStyle = isSelected
        ? "#2456d6"
        : face.shell && this.xray
        ? "rgba(38, 37, 30, 0.28)"
        : "rgba(38, 37, 30, 0.55)";
      ctx.lineWidth = isSelected ? 1.8 : 1;
      ctx.stroke();
    }

    // Draw clickable subsystem hotspots
    this.hotspots = [];
    for (const [id, meta] of Object.entries(this.partsMeta)) {
      const p = this._project(meta.center, w, h);
      this.hotspots.push({ id, x: p.x, y: p.y });
      const active = id === this.activePart;
      ctx.beginPath();
      ctx.arc(p.x, p.y, active ? 8 : 5.5, 0, Math.PI * 2);
      ctx.fillStyle = active ? "#2456d6" : "#eae9e6";
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = active ? "#ffffff" : "#26251e";
      ctx.stroke();
    }

    // Active subsystem label badge (clamped to canvas width on narrow phones)
    const activeMeta = this.partsMeta[this.activePart];
    if (activeMeta) {
      ctx.font = w < 380 ? '600 11px "JetBrains Mono", monospace' : '600 12px "JetBrains Mono", monospace';
      ctx.fillStyle = "rgba(38, 37, 30, 0.88)";
      ctx.fillText(`FOCUS: ${activeMeta.label}`, 12, 22, Math.max(120, w - 24));
    }
  }

  _loop() {
    this.yaw += (this.targetYaw - this.yaw) * 0.14;
    this.pitch += (this.targetPitch - this.pitch) * 0.14;
    this.zoom += (this.targetZoom - this.zoom) * 0.14;
    this._draw();
    requestAnimationFrame(() => this._loop());
  }
}
