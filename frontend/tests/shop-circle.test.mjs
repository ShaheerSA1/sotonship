import assert from "node:assert/strict";
import test from "node:test";
import { shopCircle } from "../src/components/shop-circle.ts";

function metresBetween([lon1,lat1], [lon2,lat2]) {
  const rad = Math.PI / 180;
  const a = Math.sin((lat2-lat1)*rad/2)**2
    + Math.cos(lat1*rad)*Math.cos(lat2*rad)*Math.sin((lon2-lon1)*rad/2)**2;
  return 2*6371008.8*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}

test("approximate shop circles are 20m across at different latitudes", () => {
  for (const center of [[-1.4061,50.9059],[0,0],[12,70]]) {
    const [ring] = shopCircle(center);
    assert.equal(ring.length, 65);
    assert.deepEqual(ring[0], ring.at(-1));
    for (const point of ring) assert(Math.abs(metresBetween(center,point)-10)<.001);
    assert(Math.abs(metresBetween(ring[0],ring[32])-20)<.001);
    assert(Math.abs(metresBetween(ring[16],ring[48])-20)<.001);
  }
});

test("invalid shop coordinates fail explicitly", () => {
  assert.throws(()=>shopCircle([NaN,50]),/valid longitude\/latitude/);
  assert.throws(()=>shopCircle([0,91]),/valid longitude\/latitude/);
});
