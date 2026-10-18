import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import ts from "typescript";

// Transpile the browser module's extensionless imports for the Node test runner.
const require = createRequire(import.meta.url);
const module = { exports: {} };
const code = ts.transpileModule(readFileSync(new URL("../src/components/map-shop-highlights.ts", import.meta.url), "utf8"), {
  compilerOptions: { target: ts.ScriptTarget.ES2023, module: ts.ModuleKind.CommonJS },
}).outputText;
new Function("require", "module", "exports", code)(
  id => require(`../src/components/${id.replace(/^\.\//, "")}.ts`), module, module.exports);
const { attachShopHighlights } = module.exports;

function setup() {
  const handlers = new Map(), updates = [], errors = [];
  const state = { zoom: 15, queryCount: 0, ready: true, shops: true, buildings: true };
  const buildings = [{ geometry: { type: "Polygon", coordinates: [[[0,0],[2,0],[2,2],[0,2],[0,0]]] } }];
  const shops = [{ id: 1, properties: { class: "grocery", name: "Test supermarket" }, geometry: { type: "Point", coordinates: [1,1] } }];
  const map = {
    on: (event, listener) => handlers.set(event, listener),
    off: (event, listener) => { assert.equal(handlers.get(event), listener); handlers.delete(event); },
    isStyleLoaded: () => true,
    isSourceLoaded: () => state.ready,
    getZoom: () => state.zoom,
    querySourceFeatures: (_source, options) => {
      state.queryCount++;
      return options.sourceLayer === "building" ? state.buildings ? buildings : [] : state.shops ? shops : [];
    },
    getSource: () => ({ setData: data => updates.push(data) }),
  };
  const detach = attachShopHighlights(map, "vector", error => errors.push(error));
  return { state, handlers, updates, errors, detach, idle: () => handlers.get("idle")() };
}

test("zooming out retains detailed shop geometry without querying simplified tiles", () => {
  const fixture = setup();
  fixture.idle();
  assert.equal(fixture.updates[0].features.length, 1);
  const queries = fixture.state.queryCount;
  for (const zoom of [13.99, 13, 12, 10, 9]) {
    fixture.state.zoom = zoom;
    fixture.state.shops = false;
    fixture.idle();
    assert.equal(fixture.updates.length, 1, `Geometry must not be cleared at zoom ${zoom}`);
    assert.equal(fixture.state.queryCount, queries, "Avoid unnecessary low-detail queries");
  }
  assert.equal(fixture.errors.length, 0);
  fixture.detach();
  assert.equal(fixture.handlers.size, 0);
});

test("switching theme while zoomed out restores the detailed shop snapshot", () => {
  const fixture = setup();
  fixture.idle();
  fixture.state.zoom = 10;
  fixture.state.ready = false;
  fixture.handlers.get("style.load")();
  fixture.idle();
  assert.equal(fixture.updates.length, 2);
  assert.deepEqual(fixture.updates[1], fixture.updates[0]);
  fixture.idle();
  assert.equal(fixture.updates.length, 2, "Source updates must not create an idle loop");
  fixture.detach();
});

test("returning to detailed zoom updates geometry for the new area", () => {
  const fixture = setup();
  fixture.idle();
  fixture.state.zoom = 10;
  fixture.idle();
  fixture.state.zoom = 14;
  fixture.state.shops = false;
  fixture.idle();
  assert.equal(fixture.updates.at(-1).features.length, 0);
  fixture.detach();
});

test("approximate shop circles survive zooming out and theme changes", () => {
  const fixture = setup();
  fixture.state.buildings = false;
  fixture.idle();
  const circle = fixture.updates[0];
  assert.equal(circle.features[0].properties.shape, "circle");
  fixture.state.zoom = 9;
  fixture.state.shops = false;
  fixture.idle();
  assert.equal(fixture.updates.length, 1);
  fixture.handlers.get("style.load")();
  fixture.idle();
  assert.deepEqual(fixture.updates[1], circle);
  fixture.detach();
});
