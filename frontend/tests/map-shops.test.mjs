import assert from "node:assert/strict";
import test from "node:test";
import { shopLayers, SHOP_FOOTPRINT_SOURCE } from "../src/components/map-shops.ts";

const layersForTest = () => shopLayers("rgba(214, 106, 23, 1)");

test("shop areas use geographic fills with no pixel-sized markers or text", () => {
  const layers = layersForTest();
  assert(layers.every(layer => layer.type === "fill"));
  assert(layers.every(layer => layer.source === SHOP_FOOTPRINT_SOURCE));
  assert(!layers.some(layer => layer.layout?.["text-field"]));
});

test("shop shapes are fully opaque orange and borderless, including overlaps", () => {
  const layers = layersForTest();
  const building = layers.find(layer => layer.source === SHOP_FOOTPRINT_SOURCE);
  assert.equal(building.type, "fill");
  assert.equal(building.paint["fill-color"], "rgba(214, 106, 23, 1)");
  assert.equal(building.paint["fill-antialias"], false);
  assert.equal(building.paint["fill-outline-color"], undefined);
  assert(!layers.some(layer => layer.type === "line"));
  assert.equal(building.paint["fill-opacity"], 1);
});

test("orange footprints have no display zoom cutoff", () => {
  const building = layersForTest().find(layer => layer.source === SHOP_FOOTPRINT_SOURCE);
  for (const zoom of [0, 9, 10, 12, 13.99, 14, 15, 20, 24]) {
    assert((building.minzoom ?? 0) <= zoom, `Orange fill must remain enabled at zoom ${zoom}`);
    assert((building.maxzoom ?? 24) >= zoom);
  }
});
