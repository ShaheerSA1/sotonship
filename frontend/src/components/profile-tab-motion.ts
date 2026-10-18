type PaneBounds = { left: number; width: number; height: number; top: number };
const mix = (from: number, to: number, t: number) => from + (to - from) * t;
const smooth = (t: number) => {
  const value = Math.max(0, Math.min(1, t));
  return value * value * (3 - 2 * value);
};

// Underdamped spring: accelerates from rest, slightly overshoots, then settles.
const DAMPING = 0.78;
const FREQUENCY = 12;
const DECAY = DAMPING * FREQUENCY;
const OSCILLATION = FREQUENCY * Math.sqrt(1 - DAMPING ** 2);
const spring = (t: number) => 1 - Math.exp(-DECAY * t) * (
  Math.cos(OSCILLATION * t) + DECAY / OSCILLATION * Math.sin(OSCILLATION * t)
);
const springSpeed = (t: number) => Math.exp(-DECAY * t)
  * FREQUENCY ** 2 / OSCILLATION * Math.sin(OSCILLATION * t);

/** Movement drives deformation; a second damped spring lets the tail lag behind. */
export function glassTravelFrames(from: PaneBounds, to: PaneBounds): Keyframe[] {
  const steps = 120;
  const dt = 1 / steps;
  const startX = from.left + from.width / 2;
  const endX = to.left + to.width / 2;
  const distance = Math.abs(endX - startX);
  const normalization = spring(1);
  let stretch = 0;
  let stretchSpeed = 0;

  return Array.from({ length: steps + 1 }, (_, index) => {
    const t = index / steps;
    const progress = spring(t) / normalization;
    const speed = Math.abs(springSpeed(t) / normalization) * distance;
    const desiredStretch = Math.min(to.width * 1.3, speed * 0.09);
    if (index > 0) {
      const acceleration = 22 ** 2 * (desiredStretch - stretch) - 2 * 0.8 * 22 * stretchSpeed;
      stretchSpeed += acceleration * dt;
      stretch += stretchSpeed * dt;
    }
    // Ease away the final residual deformation so the resting circle is exact.
    const settling = 1 - smooth((t - 0.75) / 0.25);
    const deformation = Math.max(0, stretch) * settling;
    const restingWidth = mix(from.width, to.width, smooth(t));
    const restingHeight = mix(from.height, to.height, smooth(t));
    const width = restingWidth + deformation;
    const height = restingHeight * Math.sqrt(restingWidth / width);
    const centreX = mix(startX, endX, progress);
    const centreY = mix(from.top + from.height / 2, to.top + to.height / 2, progress);
    return {
      left: `${centreX - width / 2}px`, top: `${centreY - height / 2}px`,
      width: `${width}px`, height: `${height}px`, offset: t,
      // Positions already contain the spring curve; interpolate only between samples.
      easing: "linear",
    };
  });
}
