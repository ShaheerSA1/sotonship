import type { GeographicFeature, ShopFootprints } from "./shop-building-match";
import type { MapStyle } from "./map-style";

export interface GeographicMap {
  on(event: "load" | "idle" | "style.load", listener: () => void): void;
  off(event: "load" | "idle" | "style.load", listener: () => void): void;
  isStyleLoaded(): boolean;
  isSourceLoaded(source: string): boolean;
  querySourceFeatures(source: string, options: { sourceLayer: string; filter?: unknown[] }): GeographicFeature[];
  getSource(id: string): { setData(data: ShopFootprints): void } | undefined;
  on(event: "error", listener: (event: { error: Error & { url?: string; status?: number }; sourceId?: string }) => void): void;
  setStyle(style: MapStyle): void;
  resize(): void;
  getZoom(): number;
  jumpTo(options: { zoom: number }): void;
  remove(): void;
}
interface MapRuntime {
  Map: new (options: Record<string, unknown>) => GeographicMap;
  MercatorCoordinate: {
    fromLngLat(location: [number, number]): { meterInMercatorCoordinateUnits(): number };
  };
}

// Official browser ESM distribution: no bundled worker setup is required.
const MODULE_URL = "https://unpkg.com/maplibre-gl@6.14.0/dist/maplibre-gl.mjs";
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
export async function loadMapRuntime(signal: AbortSignal) {
  const [runtime, response] = await Promise.all([
    (import(/* @vite-ignore */ MODULE_URL) as Promise<MapRuntime>).catch((error: Error) => {
      throw new Error(`Renderer request failed (${MODULE_URL}): ${error.message}`, { cause: error });
    }),
    fetch(STYLE_URL, { signal }).catch((error: Error) => {
      throw new Error(`Basemap style request failed (${STYLE_URL}): ${error.message}`, { cause: error });
    }),
  ]);
  if (!response.ok) throw new Error(`Map style request failed: HTTP ${response.status}`);
  const base: MapStyle = await response.json();
  if (base.version !== 8 || !base.sources || !Array.isArray(base.layers)) throw new Error("Map provider returned an invalid style");
  return { runtime, base };
}
