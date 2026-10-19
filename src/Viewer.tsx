import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  Box,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Maximize,
  Layers3,
  Move3D,
} from "lucide-react";
import type { Result } from "./types";
import { COLORS } from "./types";
export default function Viewer({
  result,
  selected,
  onSelect,
  compact = false,
  mode = "prediction",
}: {
  result: Result | null;
  selected: number | null;
  onSelect: (id: number) => void;
  compact?: boolean;
  mode?: string;
}) {
  const materialRef = useRef<THREE.Mesh[]>([]);
  const ref = useRef<HTMLDivElement>(null),
    api = useRef<{
      reset: () => void;
      zoom: (v: number) => void;
      wire: () => void;
    } | null>(null);
  const [wire, setWire] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    if (!ref.current || !result) return;
    const host = ref.current;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setError(
        "WebGL is unavailable. Use the face table below to inspect geometry.",
      );
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      "aria-label",
      "Interactive CAD viewport. Drag to rotate, scroll to zoom, right-drag to pan.",
    );
    renderer.domElement.tabIndex = 0;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 5000);
    camera.up.set(0, 0, 1);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    scene.add(new THREE.AmbientLight(0xffffff, 1.8));
    const light = new THREE.DirectionalLight(0xffffff, 2.5);
    light.position.set(60, -100, 200);
    scene.add(light);
    const fill = new THREE.DirectionalLight(0xd3e9e0, 1.0);
    fill.position.set(-90, 60, 40);
    scene.add(fill);
    const group = new THREE.Group();
    const meshes: THREE.Mesh[] = [];
    const resources: (THREE.BufferGeometry | THREE.Material)[] = [];
    for (const face of result.faces) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(face.positions, 3),
      );
      geo.computeVertexNormals();
      const color =
        mode === "solid"
          ? "#a1b6af"
          : mode === "disagreements"
            ? face.disagreement
              ? "#f1b567"
              : "#bacbc5"
            : COLORS[face.prediction] || COLORS.Other;
      const mat = new THREE.MeshStandardMaterial({
        color: selected === face.id ? "#e7a85f" : color,
        metalness: 0.12,
        roughness: 0.63,
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: 1,
        polygonOffsetUnits: 1,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.userData.face = face.id;
      mesh.userData.prediction = face.prediction;
      mesh.userData.disagreement = face.disagreement;
      meshes.push(mesh);
      group.add(mesh);
      const edgeGeo = new THREE.EdgesGeometry(geo, 24);
      const edgeMat = new THREE.LineBasicMaterial({
        color: 0x101d30,
        transparent: true,
        opacity: 0.75,
      });
      group.add(new THREE.LineSegments(edgeGeo, edgeMat));
      resources.push(geo, mat, edgeGeo, edgeMat);
    }
    materialRef.current = meshes;
    const bounds = new THREE.Box3().setFromObject(group),
      center = bounds.getCenter(new THREE.Vector3()),
      size = bounds.getSize(new THREE.Vector3()),
      max = Math.max(size.x, size.y, size.z);
    group.position.sub(center);
    scene.add(group);
    const grid = new THREE.GridHelper(max * 4, 32, 0xa6bdb2, 0xcbdad3);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -size.z / 2 - 0.5;
    const gm = grid.material as THREE.Material;
    gm.transparent = true;
    gm.opacity = 0.6;
    scene.add(grid);
    resources.push(grid.geometry, gm);
    const reset = () => {
      camera.position.set(max * 1.02, -max * 1.2, max * 1.15);
      controls.target.set(0, 0, 0);
      controls.update();
    };
    reset();
    api.current = {
      reset,
      zoom: (v) => {
        camera.position.multiplyScalar(v);
        controls.update();
      },
      wire: () => {
        for (const mesh of meshes)
          (mesh.material as THREE.MeshStandardMaterial).wireframe = !(
            mesh.material as THREE.MeshStandardMaterial
          ).wireframe;
      },
    };
    const raycaster = new THREE.Raycaster();
    let down = { x: 0, y: 0 };
    const pointerdown = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const click = (e: MouseEvent) => {
      if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      const r = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((e.clientX - r.left) / r.width) * 2 - 1,
          (-(e.clientY - r.top) / r.height) * 2 + 1,
        ),
        camera,
      );
      const hit = raycaster.intersectObjects(meshes)[0];
      if (hit) onSelect(hit.object.userData.face);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "0") reset();
      if (e.key === "+" || e.key === "=") api.current?.zoom(0.85);
      if (e.key === "-") api.current?.zoom(1.15);
      if (e.key.startsWith("Arrow")) {
        e.preventDefault();
        const v = camera.position.clone();
        const a =
          e.key === "ArrowLeft" ? 0.12 : e.key === "ArrowRight" ? -0.12 : 0;
        v.applyAxisAngle(new THREE.Vector3(0, 0, 1), a);
        if (e.key === "ArrowUp") v.z += max * 0.1;
        if (e.key === "ArrowDown") v.z -= max * 0.1;
        camera.position.copy(v);
        controls.update();
      }
    };
    renderer.domElement.addEventListener("pointerdown", pointerdown);
    renderer.domElement.addEventListener("click", click);
    renderer.domElement.addEventListener("keydown", key);
    const observer = new ResizeObserver(() => {
      const w = host.clientWidth,
        h = host.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    observer.observe(host);
    let frame = 0;
    const render = () => {
      frame = requestAnimationFrame(render);
      controls.update();
      renderer.render(scene, camera);
    };
    render();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      resources.forEach((r) => r.dispose());
      renderer.dispose();
      renderer.domElement.remove();
      api.current = null;
    };
  }, [result, onSelect]);
  useEffect(() => {
    for (const mesh of materialRef.current) {
      const color =
        mode === "solid"
          ? "#a1b6af"
          : mode === "disagreements"
            ? mesh.userData.disagreement
              ? "#f1b567"
              : "#bacbc5"
            : COLORS[mesh.userData.prediction] || COLORS.Other;
      (mesh.material as THREE.MeshStandardMaterial).color.set(
        selected === mesh.userData.face ? "#e7a85f" : color,
      );
    }
  }, [selected, mode, result]);
  useEffect(() => setWire(false), [result]);
  return (
    <div className={"viewport " + (compact ? "compact" : "")}>
      <div className="viewport-hud">
        <span>
          <span className="tiny-dot" /> {result?.name || "Geometry workspace"}
        </span>
        <span className="mono">{result?.face_count || "—"} faces · mm</span>
      </div>
      <div ref={ref} className="canvas-host" />
      {!result && (
        <div className="viewport-empty">
          <Box size={42} />
          <h3>Your next insight starts with a shape</h3>
          <p>Select a sample or upload a STEP model.</p>
        </div>
      )}
      {error && <div className="viewport-empty">{error}</div>}
      <div className="axis">
        <span className="axis-z">Z</span>
        <span className="axis-y">Y</span>
        <span className="axis-x">X</span>
        <Box size={30} />
      </div>
      <div className="viewer-tools">
        <button
          title="Reset camera (0)"
          aria-label="Reset camera"
          onClick={() => api.current?.reset()}
        >
          <RotateCcw size={16} />
        </button>
        <button
          title="Zoom in (+)"
          aria-label="Zoom in"
          onClick={() => api.current?.zoom(0.85)}
        >
          <ZoomIn size={16} />
        </button>
        <button
          title="Zoom out (-)"
          aria-label="Zoom out"
          onClick={() => api.current?.zoom(1.15)}
        >
          <ZoomOut size={16} />
        </button>
        <i />
        <button
          title="Toggle wireframe"
          aria-label="Toggle wireframe"
          className={wire ? "active" : ""}
          onClick={() => {
            api.current?.wire();
            setWire(!wire);
          }}
        >
          <Layers3 size={16} />
        </button>
        <button
          title="Expand viewport"
          aria-label="Expand viewport"
          onClick={() => {
            const parent = ref.current?.parentElement;
            if (document.fullscreenElement) void document.exitFullscreen();
            else void parent?.requestFullscreen();
          }}
        >
          <Maximize size={16} />
        </button>
      </div>
      <div className="viewport-foot">
        <span>
          <Move3D size={13} /> Drag to orbit <b>·</b> Scroll to zoom
        </span>
        <span className="mono">PERSPECTIVE</span>
      </div>
    </div>
  );
}
