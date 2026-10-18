import type { GeographicMap } from "./map-runtime";
import { SHOP_FILTER, SHOP_FOOTPRINT_SOURCE, SHOP_DATA_MIN_ZOOM } from "./map-shops";
import { emptyShopFootprints, shopDisplayAreas } from "./shop-building-match";

/** Reuse the basemap's loaded building footprints and retail POIs; no extra API. */
export function attachShopHighlights(map: GeographicMap, source: string, onError: (error: Error) => void) {
  let previousGeometry: string | null = null;
  let footprints = emptyShopFootprints();
  let failed = false;
  function update() {
    if (failed || !map.isStyleLoaded()) return;
    try {
      // Lower zoom tiles omit or generalise buildings and retail POIs. Retain
      // the detailed footprint snapshot instead of erasing or reclassifying it.
      if (map.getZoom() >= SHOP_DATA_MIN_ZOOM) {
        if (!map.isSourceLoaded(source)) return;
        const buildings = map.querySourceFeatures(source, { sourceLayer: "building" });
        const shops = map.querySourceFeatures(source, { sourceLayer: "poi", filter: SHOP_FILTER });
        footprints = shopDisplayAreas(buildings, shops);
      }
      const signature = JSON.stringify(footprints);
      if (signature === previousGeometry) return;
      const overlay = map.getSource(SHOP_FOOTPRINT_SOURCE);
      if (!overlay) throw new Error("Shop footprint display source is missing");
      overlay.setData(footprints);
      previousGeometry = signature;
    } catch (error) {
      failed = true;
      onError(error instanceof Error ? error : new Error(String(error)));
    }
  }
  function reset() { previousGeometry = null; }
  map.on("idle", update);
  map.on("style.load", reset);
  return () => {
    map.off("idle", update);
    map.off("style.load", reset);
  };
}
