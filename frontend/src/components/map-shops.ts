import type { MapLayer, MapStyle } from "./map-style";

export const SHOP_FOOTPRINT_SOURCE = "shop-footprints";
export const SHOP_DATA_MIN_ZOOM = 14;

// OpenMapTiles' shop grouping includes groceries and specialist retail classes.
// https://github.com/openmaptiles/openmaptiles/blob/master/layers/poi/style.json
export const SHOP_FILTER = ["any",
  ["in", "class", "shop", "grocery", "clothing_store", "alcohol_shop", "bakery", "bicycle", "butcher", "hairdresser", "music", "seafood"],
  ["in", "subclass", "books", "car_parts", "supermarket"],
];

export function shopVectorSource(base: MapStyle): string {
  const poi = base.layers.find((layer) => layer["source-layer"] === "poi" && layer.source);
  if (!poi?.source) throw new Error("Map provider has no shop/POI vector source");
  return poi.source;
}

export function shopLayers(orange: string): MapLayer[] {
  return [
    {
      id: "shop-buildings", type: "fill", source: SHOP_FOOTPRINT_SOURCE,
      paint: {
        "fill-color": orange,
        "fill-opacity": 1,
        "fill-antialias": false,
      },
    },
  ];
}
