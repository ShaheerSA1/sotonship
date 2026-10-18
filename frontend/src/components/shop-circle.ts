export type Position = [number, number];
export const APPROXIMATE_SHOP_DIAMETER_METRES = 20;
const EARTH_RADIUS_METRES = 6371008.8;

/** A geographic circle: 20 metres across on the ground, scaling with map zoom. */
export function shopCircle(center: Position): Position[][] {
  const [longitude, latitude] = center;
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)
    || Math.abs(longitude) > 180 || Math.abs(latitude) > 90) {
    throw new Error("Shop circle requires valid longitude/latitude coordinates");
  }
  const radians = Math.PI / 180;
  const lat = latitude * radians, lon = longitude * radians;
  const distance = APPROXIMATE_SHOP_DIAMETER_METRES / 2 / EARTH_RADIUS_METRES;
  const ring: Position[] = [];
  for (let index = 0; index < 64; index++) {
    const bearing = index / 64 * 2 * Math.PI;
    const nextLat = Math.asin(Math.sin(lat) * Math.cos(distance)
      + Math.cos(lat) * Math.sin(distance) * Math.cos(bearing));
    const nextLon = lon + Math.atan2(Math.sin(bearing) * Math.sin(distance) * Math.cos(lat),
      Math.cos(distance) - Math.sin(lat) * Math.sin(nextLat));
    ring.push([nextLon / radians, nextLat / radians]);
  }
  ring.push([...ring[0]]);
  return [ring];
}
