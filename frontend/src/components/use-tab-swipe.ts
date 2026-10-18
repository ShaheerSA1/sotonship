import { useRef, type TouchEvent } from "react";

/** One tab per horizontal gesture; leave vertical scrolling to the browser. */
export function useTabSwipe(onSwipe: (direction: number) => void) {
  const start = useRef<{ x: number; y: number } | null>(null);
  const reset = () => { start.current = null; };
  return {
    onTouchStart(event: TouchEvent<HTMLElement>) {
      if (event.touches.length !== 1) return reset();
      if (event.target instanceof Element && event.target.closest("input, textarea, [contenteditable]")) return reset();
      const touch = event.touches[0];
      start.current = { x: touch.clientX, y: touch.clientY };
    },
    onTouchMove(event: TouchEvent<HTMLElement>) {
      if (!start.current || event.touches.length !== 1) return reset();
      const touch = event.touches[0];
      const dx = touch.clientX - start.current.x;
      const dy = touch.clientY - start.current.y;
      if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) reset();
    },
    onTouchEnd(event: TouchEvent<HTMLElement>) {
      const origin = start.current;
      reset();
      if (!origin || event.touches.length !== 0) return;
      const touch = event.changedTouches[0];
      const dx = touch.clientX - origin.x;
      const dy = touch.clientY - origin.y;
      if (Math.abs(dx) >= 40 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        onSwipe(dx < 0 ? 1 : -1);
      }
    },
    onTouchCancel: reset,
  };
}
