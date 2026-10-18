export const LENS_SLICE_COUNT = 15;

/** Build vector-only strips: strongest bend at the lens centre, normal at its edges. */
export function glassLensFrame(frame: Keyframe) {
  const left = parseFloat(String(frame.left));
  const top = parseFloat(String(frame.top));
  const width = parseFloat(String(frame.width));
  const height = parseFloat(String(frame.height));
  const centreX = left + width / 2;
  const centreY = top + height / 2;
  const offset = frame.offset;
  const easing = frame.easing;
  return {
    slices: Array.from({ length: LENS_SLICE_COUNT }, (_, index) => {
      const start = index / LENS_SLICE_COUNT;
      const middle = (index + 0.5) / LENS_SLICE_COUNT;
      const strength = Math.sin(Math.PI * middle) ** 2;
      const scaleX = 1 + 0.14 * strength;
      const scaleY = 1 + 0.08 * strength;
      return {
        clip: {
          x: `${left + width * start}px`,
          y: `${top}px`,
          width: `${width / LENS_SLICE_COUNT + 0.15}px`,
          height: `${height}px`,
          offset, easing,
        },
        content: {
          transform: `matrix(${scaleX}, 0, 0, ${scaleY}, ${(1 - scaleX) * centreX}, ${(1 - scaleY) * centreY})`,
          offset, easing,
        },
      };
    }),
  };
}
