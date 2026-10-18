import { useEffect, useLayoutEffect, useRef } from "react";

/** Keep each surviving row at its old position, then let rows follow one another. */
export function useListReflow(revision: unknown) {
  const rows = useRef(new Map<number, HTMLLIElement>());
  const before = useRef<Map<number, number> | null>(null);
  const animations = useRef(new Map<number, Animation>());

  function capture() {
    before.current = new Map([...rows.current].map(([id, row]) => [id, row.getBoundingClientRect().top]));
  }

  useLayoutEffect(() => {
    const positions = before.current;
    if (!positions) return;
    before.current = null;
    for (const animation of animations.current.values()) animation.cancel();
    animations.current.clear();
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let order = 0;
    for (const [id, row] of rows.current) {
      const oldTop = positions.get(id);
      if (oldTop === undefined) continue;
      const delta = oldTop - row.getBoundingClientRect().top;
      if (Math.abs(delta) < 0.5) continue;
      const animation = row.animate([
        { transform: `translateY(${delta}px)` },
        { transform: "translateY(0)" },
      ], {
        duration: 260,
        delay: Math.min(order++ * 35, 245),
        easing: "cubic-bezier(0.22, 1, 0.36, 1)",
        fill: "backwards",
      });
      animations.current.set(id, animation);
      animation.onfinish = () => {
        if (animations.current.get(id) === animation) animations.current.delete(id);
      };
    }
  }, [revision]);

  useEffect(() => {
    const active = animations.current;
    return () => { for (const animation of active.values()) animation.cancel(); };
  }, []);

  return { rows, capture };
}
