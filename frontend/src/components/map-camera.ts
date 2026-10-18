// Southampton Civic Centre, Historic England listing via Planning Data:
// https://www.planning.data.gov.uk/entity/31549436
export const CIVIC_CENTRE: [number, number] = [-1.406496, 50.90801];
export const INITIAL_HORIZONTAL_SPAN_METRES = 500;
const WORLD_SIZE_AT_ZOOM_ZERO = 512;

/** Use CSS pixels and the renderer's own Mercator metre conversion. */
export function zoomForHorizontalSpan(width: number, mercatorUnitsPerMetre: number, metres = INITIAL_HORIZONTAL_SPAN_METRES) {
  if (![width, mercatorUnitsPerMetre, metres].every((value) => Number.isFinite(value) && value > 0)) {
    throw new Error("Map width, Mercator scale and horizontal span must be positive finite numbers");
  }
  return Math.log2(width / (WORLD_SIZE_AT_ZOOM_ZERO * metres * mercatorUnitsPerMetre));
}
