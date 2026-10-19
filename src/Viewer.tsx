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
  Loader2,
  MousePointer2,
  Scan,
} from "lucide-react";
import type { Result } from "./types";
import { COLORS } from "./types";
import { fitGeometry } from "./cameraFit";
export default function Viewer({
  result,
  selected,
  onSelect,
  compact = false,
  mode = "prediction",
  busy = false,
}: {
  result: Result | null;
  selected: number | null;
  onSelect: (id: number) => void;
  compact?: boolean;
  mode?: string;
  busy?: boolean;
}) {
  const materialRef = useRef<THREE.Mesh[]>([]);
  const ref = useRef<HTMLDivElement>(null),
    api = useRef<{
      reset: () => void;
      zoom: (v: number) => void;
      wire: () => void;
      focus: (id: number) => void;
    } | null>(null);
  const [wire, setWire] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    if (!ref.current || !result) return;
    setError("");
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
      mesh.userData.alternate = face.candidate;
      meshes.push(mesh);
      group.add(mesh);
      const edgeGeo = new THREE.EdgesGeometry(geo, 24);
      const edgeMat = new THREE.LineBasicMaterial({
        color: 0x101d30,
        transparent: true,
        opacity: 0.75,
      });
      const edges = new THREE.LineSegments(edgeGeo, edgeMat);
      mesh.userData.edges = edges;
      group.add(edges);
      resources.push(geo, mat, edgeGeo, edgeMat);
    }
    materialRef.current = meshes;
    const bounds = new THREE.Box3().setFromObject(group),
      center = bounds.getCenter(new THREE.Vector3()),
      size = bounds.getSize(new THREE.Vector3()),
      max = Math.max(size.x, size.y, size.z);
    group.position.sub(center);
    scene.add(group);
    camera.near = Math.max(max / 10000, 0.000001);
    camera.far = max * 1000;
    controls.minDistance = max * 0.15;
    controls.maxDistance = max * 30;
    const points = result.faces.flatMap((face) => {
      const vertices: THREE.Vector3[] = [];
      for (let i = 0; i < face.positions.length; i += 3)
        vertices.push(
          new THREE.Vector3(
            ...(face.positions.slice(i, i + 3) as [number, number, number]),
          ).sub(center),
        );
      return vertices;
    });
    const grid = new THREE.GridHelper(max * 5, 50, 0xb4c9be, 0xd5e1da);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -size.z / 2 - max * 0.008;
    const gm = grid.material as THREE.Material;
    gm.transparent = true;
    gm.opacity = 0.48;
    scene.add(grid);
    resources.push(grid.geometry, gm);
    const direction = new THREE.Vector3(1, -1.25, 1.05);
    const reset = () => {
      const fit = fitGeometry(points, direction, camera.fov, camera.aspect);
      camera.position.copy(fit.position);
      controls.target.copy(fit.target);
      controls.update();
    };
    reset();
    api.current = {
      reset,
      focus: (id) => {
        const mesh = meshes.find((m) => m.userData.face === id);
        if (!mesh) return;
        const positions = mesh.geometry.getAttribute("position");
        const normals = mesh.geometry.getAttribute("normal");
        const facePoints: THREE.Vector3[] = [];
        const normal = new THREE.Vector3();
        for (let i = 0; i < positions.count; i++) {
          facePoints.push(
            new THREE.Vector3()
              .fromBufferAttribute(positions, i)
              .add(group.position),
          );
          normal.add(new THREE.Vector3().fromBufferAttribute(normals, i));
        }
        if (normal.length() < 0.01)
          normal.copy(camera.position).sub(controls.target);
        normal.normalize();
        // An axial view needs a nonparallel camera up vector for a valid basis.
        if (Math.abs(normal.z) > 0.98)
          normal.add(new THREE.Vector3(0.12, -0.12, 0)).normalize();
        const fit = fitGeometry(
          facePoints,
          normal,
          camera.fov,
          camera.aspect,
          0.72,
        );
        controls.target.copy(fit.target);
        camera.position
          .copy(fit.target)
          .addScaledVector(normal, Math.max(fit.distance, max * 0.6));
        controls.update();
      },
      zoom: (v) => {
        camera.position
          .sub(controls.target)
          .multiplyScalar(v)
          .add(controls.target);
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
        const v = camera.position.clone().sub(controls.target);
        const a =
          e.key === "ArrowLeft" ? 0.12 : e.key === "ArrowRight" ? -0.12 : 0;
        v.applyAxisAngle(new THREE.Vector3(0, 0, 1), a);
        if (e.key === "ArrowUp") v.z += max * 0.1;
        if (e.key === "ArrowDown") v.z -= max * 0.1;
        camera.position.copy(v.add(controls.target));
        controls.update();
      }
    };
    renderer.domElement.addEventListener("pointerdown", pointerdown);
    renderer.domElement.addEventListener("click", click);
    renderer.domElement.addEventListener("keydown", key);
    let initialSize = true;
    const observer = new ResizeObserver(() => {
      const w = host.clientWidth,
        h = host.clientHeight;
      renderer.setSize(w, h);
      if (!w || !h) return;
      const viewDirection = camera.position
        .clone()
        .sub(controls.target)
        .normalize();
      const oldFit = fitGeometry(
        points,
        viewDirection,
        camera.fov,
        camera.aspect,
      );
      const zoomRatio =
        camera.position.distanceTo(controls.target) / oldFit.distance;
      camera.aspect = w / h;
      if (initialSize) {
        reset();
        initialSize = false;
      } else {
        const nextFit = fitGeometry(
          points,
          viewDirection,
          camera.fov,
          camera.aspect,
        );
        camera.position
          .copy(controls.target)
          .addScaledVector(viewDirection, nextFit.distance * zoomRatio);
      }
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
            : COLORS[
                mode === "alternate"
                  ? mesh.userData.alternate || mesh.userData.prediction
                  : mesh.userData.prediction
              ] || COLORS.Other;
      const isSelected = selected === mesh.userData.face;
      const material = mesh.material as THREE.MeshStandardMaterial;
      material.color.set(isSelected ? "#e7a85f" : color);
      material.emissive.set(isSelected ? "#744312" : "#000000");
      material.emissiveIntensity = isSelected ? 0.1 : 0;
      const edgeMaterial = mesh.userData.edges
        .material as THREE.LineBasicMaterial;
      edgeMaterial.color.set(isSelected ? "#874b13" : "#344b43");
      edgeMaterial.opacity = isSelected ? 1 : 0.6;
      edgeMaterial.depthTest = !isSelected;
      mesh.userData.edges.renderOrder = isSelected ? 2 : 0;
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
      <div ref={ref} className="canvas-host" aria-busy={busy} />
      {selected !== null && result && (
        <div className="selection-chip">
          <MousePointer2 size={13} />
          <strong>Face {String(selected + 1).padStart(3, "0")}</strong>
          <span>Selected · amber surface</span>
        </div>
      )}
      {busy && (
        <div className="viewport-processing" role="status">
          <Loader2 size={17} className="spin" />
          <div>
            <strong>Analyzing geometry</strong>
            <span>
              {result
                ? "Previous result remains visible until processing completes."
                : "Preparing CAD surfaces and running the selected model."}
            </span>
          </div>
        </div>
      )}
      {!result && !busy && (
        <div className="viewport-empty">
          <Box size={42} />
          <h3>No geometry loaded</h3>
          <p>
            Choose a sample and run inference, or upload a closed-solid STEP
            file.
          </p>
        </div>
      )}
      {error && (
        <div className="viewport-empty" role="alert">
          <Box size={30} />
          <h3>3D rendering unavailable</h3>
          <p>{error}</p>
        </div>
      )}
      <div className="axis">
        <span className="axis-z">Z</span>
        <span className="axis-y">Y</span>
        <span className="axis-x">X</span>
        <Box size={30} />
      </div>
      <div className="viewer-tools">
        <button
          disabled={!result || !!error}
          title="Reset camera (0)"
          aria-label="Reset camera"
          onClick={() => api.current?.reset()}
        >
          <RotateCcw size={16} />
        </button>
        {selected !== null && (
          <button
            disabled={!result || !!error}
            title="Focus selected face"
            aria-label="Focus selected face"
            onClick={() => api.current?.focus(selected)}
          >
            <Scan size={16} />
          </button>
        )}
        <button
          disabled={!result || !!error}
          title="Zoom in (+)"
          aria-label="Zoom in"
          onClick={() => api.current?.zoom(0.85)}
        >
          <ZoomIn size={16} />
        </button>
        <button
          disabled={!result || !!error}
          title="Zoom out (-)"
          aria-label="Zoom out"
          onClick={() => api.current?.zoom(1.15)}
        >
          <ZoomOut size={16} />
        </button>
        <i />
        <button
          disabled={!result || !!error}
          title="Toggle wireframe"
          aria-label="Toggle wireframe"
          aria-pressed={wire}
          className={wire ? "active" : ""}
          onClick={() => {
            api.current?.wire();
            setWire(!wire);
          }}
        >
          <Layers3 size={16} />
        </button>
        <button
          disabled={!result || !!error}
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
