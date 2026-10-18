import { shopCircle, type Position } from "./shop-circle.ts";
export type GeographicFeature = {
  id?: string | number;
  properties?: Record<string, unknown>;
  geometry: { type: string; coordinates: unknown };
};
export type ShopFootprints = {
  type: "FeatureCollection";
  features: { type: "Feature"; properties: { shape: "footprint" | "circle" }; geometry: { type: "Polygon"; coordinates: Position[][] } }[];
};

export function emptyShopFootprints(): ShopFootprints { return { type: "FeatureCollection", features: [] }; }

function inRing(point: Position, ring: Position[]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[j], b = ring[i];
    const cross = (point[0] - a[0]) * (b[1] - a[1]) - (point[1] - a[1]) * (b[0] - a[0]);
    if (Math.abs(cross) <= 1e-12
      && point[0] >= Math.min(a[0], b[0]) - 1e-10 && point[0] <= Math.max(a[0], b[0]) + 1e-10
      && point[1] >= Math.min(a[1], b[1]) - 1e-10 && point[1] <= Math.max(a[1], b[1]) + 1e-10) {
      return { inside: true, boundary: true };
    }
    if ((a[1] > point[1]) !== (b[1] > point[1])
      && point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return { inside, boundary: false };
}

function inPolygon(point: Position, polygon: Position[][]) {
  const outer = inRing(point, polygon[0]);
  if (!outer.inside || outer.boundary) return outer.inside;
  for (const hole of polygon.slice(1)) {
    const result = inRing(point, hole);
    if (result.boundary) return true;
    if (result.inside) return false;
  }
  return true;
}

/** Use independent store footprints; otherwise show the requested 20m location circle. */
export function shopDisplayAreas(buildings: GeographicFeature[], shops: GeographicFeature[]): ShopFootprints {
  const points = shops.filter((shop) => shop.geometry.type === "Point"
    && !["no", "vacant"].includes(String(shop.properties?.subclass)))
    .map((shop) => ({
      position: shop.geometry.coordinates as Position,
      key: shop.id === undefined ? JSON.stringify([shop.geometry.coordinates, shop.properties]) : String(shop.id),
      shared: shop.properties?.subclass === "mall" || shop.properties?.class === "mall",
    }));
  const result = emptyShopFootprints();
  const matched = new Set<string>();
  const representedShops = new Set<string>();
  for (const building of buildings) {
    const polygons = building.geometry.type === "Polygon" ? [building.geometry.coordinates as Position[][]]
      : building.geometry.type === "MultiPolygon" ? building.geometry.coordinates as Position[][][] : [];
    for (const polygon of polygons) {
      if (!polygon[0]?.length) continue;
      const xs = polygon[0].map((point) => point[0]), ys = polygon[0].map((point) => point[1]);
      const west = Math.min(...xs), east = Math.max(...xs), south = Math.min(...ys), north = Math.max(...ys);
      const occupants = points.filter(({ position: point }) => point[0] >= west && point[0] <= east
        && point[1] >= south && point[1] <= north && inPolygon(point, polygon));
      // Multiple shops locate tenants, not their walls. Keep the parent neutral
      // including connected mall wings; unmatched tenants get circles below.
      if (occupants.some(point => point.shared)) continue;
      if (new Set(occupants.map(point => point.key)).size === 1) {
        const key = JSON.stringify(polygon);
        if (matched.has(key)) continue;
        matched.add(key);
        result.features.push({ type: "Feature", properties: { shape: "footprint" }, geometry: { type: "Polygon", coordinates: polygon } });
        occupants.forEach(point => representedShops.add(point.key));
      }
    }
  }
  for (const point of points) {
    if (point.shared || representedShops.has(point.key)) continue;
    representedShops.add(point.key);
    result.features.push({ type: "Feature", properties: { shape: "circle" },
      geometry: { type: "Polygon", coordinates: shopCircle(point.position) } });
  }
  return result;
}
