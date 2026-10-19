import * as THREE from "three";

/** Fit real surface vertices, including perspective depth, to the available frustum. */
export function fitGeometry(
  points: THREE.Vector3[],
  direction: THREE.Vector3,
  verticalFov: number,
  aspect: number,
  occupancy = 0.86,
) {
  const out = direction.clone().normalize();
  const referenceUp =
    Math.abs(out.z) > 0.999
      ? new THREE.Vector3(0, 1, 0)
      : new THREE.Vector3(0, 0, 1);
  const right = new THREE.Vector3().crossVectors(referenceUp, out).normalize();
  const up = new THREE.Vector3().crossVectors(out, right).normalize();
  const projected = points.map(
    (p) => new THREE.Vector3(p.dot(right), p.dot(up), p.dot(out)),
  );
  const box = new THREE.Box3().setFromPoints(projected);
  const center = box.getCenter(new THREE.Vector3());
  const tanY = Math.tan(THREE.MathUtils.degToRad(verticalFov / 2)) * occupancy;
  const tanX = tanY * Math.max(aspect, 0.01);
  let lowerX = -Infinity,
    upperX = Infinity,
    lowerY = -Infinity,
    upperY = Infinity;
  for (const p of projected) {
    lowerX = Math.max(lowerX, p.x + tanX * p.z);
    upperX = Math.min(upperX, p.x - tanX * p.z);
    lowerY = Math.max(lowerY, p.y + tanY * p.z);
    upperY = Math.min(upperY, p.y - tanY * p.z);
  }
  const depth = Math.max(
    (lowerX - upperX) / (2 * tanX),
    (lowerY - upperY) / (2 * tanY),
    box.max.z +
      Math.max(box.getSize(new THREE.Vector3()).length() * 0.001, 1e-8),
  );
  // Center the perspective silhouette, rather than the world-space bounding box.
  const lo = box.min.clone(),
    hi = box.max.clone();
  for (let iteration = 0; iteration < 18; iteration++) {
    const cx = (lo.x + hi.x) / 2,
      cy = (lo.y + hi.y) / 2;
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;
    for (const p of projected) {
      const x = (p.x - cx) / (depth - p.z),
        y = (p.y - cy) / (depth - p.z);
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
    if (minX + maxX > 0) lo.x = cx;
    else hi.x = cx;
    if (minY + maxY > 0) lo.y = cy;
    else hi.y = cy;
  }
  const target = right
    .clone()
    .multiplyScalar((lo.x + hi.x) / 2)
    .addScaledVector(up, (lo.y + hi.y) / 2)
    .addScaledVector(out, center.z);
  const distance = depth - center.z;
  return {
    target,
    position: target.clone().addScaledVector(out, distance),
    distance,
  };
}
