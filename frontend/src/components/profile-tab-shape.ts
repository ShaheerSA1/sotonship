export type GlassShapeBounds = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const KAPPA = 0.5522847498;
const point = (value: number) => Number(value.toFixed(3));

function capsulePath(bounds: GlassShapeBounds) {
  const { left, top, width, height } = bounds;
  const right = left + width;
  const bottom = top + height;
  const radius = height / 2;
  const control = radius * KAPPA;
  return [
    `M ${point(left + radius)} ${point(top)}`,
    `L ${point(right - radius)} ${point(top)}`,
    `C ${point(right - radius + control)} ${point(top)} ${point(right)} ${point(top + radius - control)} ${point(right)} ${point(top + radius)}`,
    `C ${point(right)} ${point(top + radius + control)} ${point(right - radius + control)} ${point(bottom)} ${point(right - radius)} ${point(bottom)}`,
    `L ${point(left + radius)} ${point(bottom)}`,
    `C ${point(left + radius - control)} ${point(bottom)} ${point(left)} ${point(top + radius + control)} ${point(left)} ${point(top + radius)}`,
    `C ${point(left)} ${point(top + radius - control)} ${point(left + radius - control)} ${point(top)} ${point(left + radius)} ${point(top)}`,
    "Z",
  ].join(" ");
}

/** One rounded head with a smoothly tapered rear, mirrored with travel direction. */
export function glassShapePath(main: GlassShapeBounds, direction = 1) {
  const { left, top, width, height } = main;
  if (width <= height + 0.01) return capsulePath(main);
  const r = height / 2;
  const head = width - r;
  const middle = top + r;
  const bottom = top + height;
  const c = r * KAPPA;
  // Keep a substantial rear radius even at maximum stretch.
  const elongation = Math.max(0, Math.min(1, (width - height) / height));
  const tailRadius = r * (1 - 0.35 * elongation);
  const tailControl = tailRadius * KAPPA;
  const reach = (head - tailRadius) * 0.4;
  const x = (u: number) => point(direction >= 0 ? left + u : left + width - u);
  return [
    `M ${x(tailRadius)} ${point(middle - tailRadius)}`,
    `C ${x(tailRadius + reach)} ${point(middle - tailRadius)} ${x(head - reach)} ${point(top)} ${x(head)} ${point(top)}`,
    `C ${x(head + c)} ${point(top)} ${x(width)} ${point(middle - c)} ${x(width)} ${point(middle)}`,
    `C ${x(width)} ${point(middle + c)} ${x(head + c)} ${point(bottom)} ${x(head)} ${point(bottom)}`,
    `C ${x(head - reach)} ${point(bottom)} ${x(tailRadius + reach)} ${point(middle + tailRadius)} ${x(tailRadius)} ${point(middle + tailRadius)}`,
    `C ${x(tailRadius - tailControl)} ${point(middle + tailRadius)} ${x(0)} ${point(middle + tailControl)} ${x(0)} ${point(middle)}`,
    `C ${x(0)} ${point(middle - tailControl)} ${x(tailRadius - tailControl)} ${point(middle - tailRadius)} ${x(tailRadius)} ${point(middle - tailRadius)}`,
    "Z",
  ].join(" ");
}
