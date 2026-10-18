import { shopLayers, SHOP_FOOTPRINT_SOURCE } from "./map-shops";
import { emptyShopFootprints } from "./shop-building-match";

export type MapLayer = {
  id: string; type: string; source?: string; "source-layer"?: string;
  layout?: Record<string, unknown>; paint?: Record<string, unknown>;
  [key: string]: unknown;
};
export type MapStyle = { version: 8; sources: Record<string, unknown>; layers: MapLayer[]; [key: string]: unknown };

function opacity(colour: string, alpha: number) {
  const channels = colour.match(/[\d.]+/g);
  if (!channels || channels.length !== 4) throw new Error(`Map palette must use RGBA: ${colour}`);
  return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
}

function soften(colour: string, saturation: number, lightening: number) {
  const channels = colour.match(/[\d.]+/g)?.map(Number);
  if (!channels || channels.length !== 4) throw new Error(`Map palette must use RGBA: ${colour}`);
  const [r, g, b, alpha] = channels;
  const midpoint = (Math.min(r, g, b) + Math.max(r, g, b)) / 2;
  const softened = [r, g, b].map(channel => {
    const muted = midpoint + (channel - midpoint) * saturation;
    return Math.round(muted + (255 - muted) * lightening);
  });
  return `rgba(${softened.join(", ")}, ${alpha})`;
}

/** Render real vector geography with our own small set of neutral map layers. */
export function createMapStyle(base: MapStyle, host: HTMLElement, dark: boolean): MapStyle {
  const css = getComputedStyle(host);
  const colour = (id: string) => {
    const value = css.getPropertyValue(`--colour-${id}`).trim();
    if (!value) throw new Error(`Missing map palette entry ${id}`);
    return value;
  };
  const background = colour(dark ? "c02" : "c01");
  const text = colour(dark ? "c01" : "c02");
  const muted = colour("c03");
  const road = colour(dark ? "c03" : "white");
  const transport = base.layers.find((layer) => layer["source-layer"] === "transportation");
  if (!transport?.source) throw new Error("Map provider style has no transportation vector source");
  const source = transport.source;
  const roads = ["in", "class", "motorway", "trunk", "primary", "secondary", "tertiary", "minor", "service"];
  return {
    version: 8,
    sources: {
      ...base.sources,
      [SHOP_FOOTPRINT_SOURCE]: { type: "geojson", data: emptyShopFootprints(), tolerance: 0 },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": background } },
      { id: "parks", type: "fill", source, "source-layer": "landcover",
        filter: ["in", "class", "grass", "wood"], paint: { "fill-color": opacity(text, 0.06) } },
      { id: "park-boundaries", type: "fill", source, "source-layer": "park", paint: { "fill-color": opacity(text, 0.05) } },
      { id: "water", type: "fill", source, "source-layer": "water", paint: { "fill-color": opacity(muted, dark ? 0.22 : 0.18) } },
      { id: "road-edges", type: "line", source, "source-layer": "transportation", filter: roads,
        layout: { "line-cap": "round", "line-join": "round" }, paint: {
          "line-color": opacity(text, 0.12), "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.8, 13, 2.5, 16, 7],
        } },
      { id: "roads", type: "line", source, "source-layer": "transportation", filter: roads,
        layout: { "line-cap": "round", "line-join": "round" }, paint: {
          "line-color": road, "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.4, 13, 1.5, 16, 5],
        } },
      ...shopLayers(soften(colour("c27"), 0.6, 0.25)),
    ],
  };
}
