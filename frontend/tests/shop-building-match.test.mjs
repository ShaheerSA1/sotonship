import assert from "node:assert/strict";
import test from "node:test";
import { shopDisplayAreas } from "../src/components/shop-building-match.ts";

const ring = (x = 0, y = 0, size = 2) => [[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]];
const polygon = (coordinates) => ({ geometry: { type: "Polygon", coordinates } });
const point = (x, y, id = 1, properties = { class: "shop" }) => ({ id, properties, geometry: { type: "Point", coordinates: [x,y] } });

test("a shop in one merged building does not colour its disconnected neighbours", () => {
  const shop = [ring()], otherShop = [ring(5,0)], residential = [ring(10,0)];
  const merged = { geometry: { type: "MultiPolygon", coordinates: [shop, otherShop, residential] } };
  const before = JSON.stringify(merged);
  const output = shopDisplayAreas([merged], [point(1,1,1), point(6,1,2)]);
  assert.deepEqual(output.features.map(feature => feature.geometry.coordinates), [shop, otherShop]);
  assert.equal(JSON.stringify(merged), before, "Source geometry must not be mutated");
});

test("shops in courtyards or outside buildings get circles, without colouring neighbouring footprints", () => {
  const outer = ring(0,0,4), hole = ring(1,1,2);
  const building = polygon([outer, hole]);
  const unmatched = shopDisplayAreas([building], [point(2,2,1), point(5,2,2)]);
  assert.equal(unmatched.features.length, 2);
  assert(unmatched.features.every(feature => feature.properties.shape === "circle"));
  const output = shopDisplayAreas([building], [point(.5,.5)]);
  assert.deepEqual(output.features[0].geometry.coordinates, [outer, hole]);
});

test("repeated tiles and multiple shop points do not duplicate a footprint", () => {
  const building = polygon([ring()]);
  assert.equal(shopDisplayAreas([building, building], [point(1,1), point(1.5,1)]).features.length, 1);
});

test("a shared building remains neutral instead of colouring all tenants and non-shop space", () => {
  const coordinates = [ring()];
  const output = shopDisplayAreas([polygon(coordinates)], [point(.5,1,1), point(1.5,1,2)]);
  assert.equal(output.features.length, 2);
  assert(output.features.every(feature => feature.properties.shape === "circle"));
});

test("a mall parent is excluded even when it contains only one mapped retailer", () => {
  const output = shopDisplayAreas([polygon([ring()])], [point(.5,1), point(1.5,1,2,{ class: "shop", subclass: "mall" })]);
  assert.equal(output.features.length, 1);
  assert.equal(output.features[0].properties.shape, "circle");
});

test("real shop-unit polygons remain eligible inside an excluded shared outline", () => {
  const parent = polygon([ring(0,0,8)]), unitA = polygon([ring(1,1)]), unitB = polygon([ring(4,1)]);
  const output = shopDisplayAreas([parent,unitA,unitB], [point(2,2,1),point(5,2,2),point(4,6,3,{class:"shop",subclass:"mall"})]);
  assert.deepEqual(output.features.map(feature=>feature.geometry.coordinates), [unitA.geometry.coordinates,unitB.geometry.coordinates]);
});

test("a standalone supermarket stays orange when its POI is repeated across tiles", () => {
  const asda = point(1,1,42,{name:"Asda",class:"grocery",subclass:"supermarket"});
  const output = shopDisplayAreas([polygon([ring()])], [asda,asda]);
  assert.equal(output.features.length, 1);
  assert.equal(output.features[0].properties.shape, "footprint");
});

test("CeX without a unit boundary gets one circle, including repeated tile records", () => {
  const cex = point(-1.4061,50.9059,1,{name:"CeX",class:"shop",subclass:"electronics"});
  const output = shopDisplayAreas([], [cex,cex]);
  assert.equal(output.features.length, 1);
  assert.equal(output.features[0].properties.shape, "circle");
});

test("malls and vacant units never receive approximate shop circles", () => {
  const output = shopDisplayAreas([], [point(0,0,1,{class:"shop",subclass:"mall"}),
    point(0,0,2,{class:"shop",subclass:"vacant"}),point(0,0,3,{class:"shop",subclass:"no"})]);
  assert.equal(output.features.length, 0);
});
