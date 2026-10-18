import { useCallback, useId, useLayoutEffect, useRef } from "react";
import { glassTravelFrames } from "./profile-tab-motion";
import type { ProfileTabLensRefs } from "./profile-tab-lens-refs";
import { glassLensFrame } from "./profile-tab-lens";
import { glassShapePath, type GlassShapeBounds } from "./profile-tab-shape";

export type TabGlassGeometry = {
  height: number;
  tabs: { left: number; width: number; top: number }[];
};

const PROFILE_TAB_GLASS_DIAMETER = 40.32;

function applyLensFrame(frame: Keyframe, lensRefs: ProfileTabLensRefs) {
  const lensFrame = glassLensFrame(frame);
  lensFrame.slices.forEach((slice, index) => {
    const sliceLens = lensRefs.sliceLenses.current[index];
    const sliceContent = lensRefs.sliceContents.current[index];
    if (!sliceLens || !sliceContent) {
      throw new Error(`[profile-tabs] refraction slice ${index} is not mounted`);
    }
    for (const property of ["x", "y", "width", "height"] as const) {
      sliceLens.style.setProperty(property, slice.clip[property]);
    }
    sliceContent.style.transform = slice.content.transform;
  });
}

export function ProfileTabGlass({
  geometry, activeTab, lensRefs,
}: {
  geometry: TabGlassGeometry;
  activeTab: number;
  lensRefs: ProfileTabLensRefs;
}) {
  const pane = useRef<HTMLDivElement>(null);
  const surfacePath = useRef<SVGPathElement>(null);
  const topShinePath = useRef<SVGPathElement>(null);
  const lowerReflectionPath = useRef<SVGPathElement>(null);
  const depthPath = useRef<SVGPathElement>(null);
  const topGradient = useRef<SVGRadialGradientElement>(null);
  const lowerGradient = useRef<SVGRadialGradientElement>(null);
  const depthGradient = useRef<SVGLinearGradientElement>(null);
  const animation = useRef<Animation | null>(null);
  const lensFrameRequest = useRef<number | null>(null);
  const previousTab = useRef<number | null>(null);
  const gradientId = `${useId().replaceAll(":", "")}-profile-glass`;

  const drawShape = useCallback((
    main: GlassShapeBounds,
    direction = 1,
  ) => {
    const path = glassShapePath(main, direction);
    surfacePath.current!.setAttribute("d", path);
    // Share the visible outline with both masks: normal outside, enlarged inside.
    for (const lens of [lensRefs.insideLens.current, lensRefs.outsideLens.current]) {
      if (!lens) throw new Error("[profile-tabs] shared lens path is not mounted");
      lens.setAttribute("d", path);
    }
    for (const layer of [topShinePath, lowerReflectionPath, depthPath]) {
      layer.current!.setAttribute("d", path);
    }
    const shadingBounds = main;
    const mainHeight = shadingBounds.height;
    topGradient.current!.setAttribute("gradientTransform",
      `translate(${shadingBounds.left + shadingBounds.width - mainHeight * 0.35} ${shadingBounds.top}) scale(${mainHeight * 1.7} ${mainHeight * 0.9})`);
    lowerGradient.current!.setAttribute("gradientTransform",
      `translate(${shadingBounds.left + mainHeight * 0.12} ${shadingBounds.top + shadingBounds.height * 0.92}) scale(${mainHeight * 1.4} ${mainHeight * 0.86})`);
    depthGradient.current!.setAttribute("x1", String(shadingBounds.left + shadingBounds.width));
    depthGradient.current!.setAttribute("y1", String(shadingBounds.top));
    depthGradient.current!.setAttribute("x2", String(shadingBounds.left + shadingBounds.width - Math.min(shadingBounds.width, mainHeight * 2.5)));
    depthGradient.current!.setAttribute("y2", String(shadingBounds.top + shadingBounds.height));
  }, [lensRefs]);

  useLayoutEffect(() => {
    const element = pane.current!;
    const tab = geometry.tabs[activeTab];
    const width = PROFILE_TAB_GLASS_DIAMETER;
    const target = {
      left: tab.left + (tab.width - width) / 2,
      width,
      height: PROFILE_TAB_GLASS_DIAMETER,
      top: (geometry.height - PROFILE_TAB_GLASS_DIAMETER) / 2 + tab.top,
    };
    const initialized = previousTab.current !== null;
    const selectedAnotherTab = initialized && previousTab.current !== activeTab;
    // Sample before cancelling so rapid reversals start at the visible position.
    const rendered = getComputedStyle(element);
    const from = initialized
      ? {
        left: parseFloat(rendered.left), width: parseFloat(rendered.width),
        height: parseFloat(rendered.height), top: parseFloat(rendered.top),
      }
      : target;

    animation.current?.cancel();
    animation.current = null;
    if (lensFrameRequest.current !== null) cancelAnimationFrame(lensFrameRequest.current);
    lensFrameRequest.current = null;

    element.style.left = `${target.left}px`;
    element.style.width = `${target.width}px`;
    element.style.top = `${target.top}px`;
    element.style.height = `${target.height}px`;
    applyLensFrame({
      left: `${target.left}px`, top: `${target.top}px`,
      width: `${target.width}px`, height: `${target.height}px`,
    }, lensRefs);
    drawShape(target);
    previousTab.current = activeTab;

    if (!selectedAnotherTab || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const direction = target.left + target.width / 2 >= from.left + from.width / 2 ? 1 : -1;
    const timing = { duration: 1_000, easing: "linear" };
    const travel = element.animate(glassTravelFrames(from, target), timing);
    const startTime = document.timeline.currentTime;
    travel.startTime = startTime;
    animation.current = travel;
    // One finite sampler keeps both the vector lens and single glass silhouette aligned.
    const syncLens = () => {
      const current = getComputedStyle(element);
      const mainBounds = {
        left: current.left, top: current.top, width: current.width, height: current.height,
      };
      applyLensFrame(mainBounds, lensRefs);
      const movingBounds = {
        left: parseFloat(current.left), top: parseFloat(current.top),
        width: parseFloat(current.width), height: parseFloat(current.height),
      };
      drawShape(movingBounds, direction);
      const mainFinished = travel.playState === "finished" || travel.playState === "idle";
      if (mainFinished) {
        drawShape(target);
        lensFrameRequest.current = null;
        animation.current = null;
        return;
      }
      lensFrameRequest.current = requestAnimationFrame(syncLens);
    };
    lensFrameRequest.current = requestAnimationFrame(syncLens);
  }, [geometry, activeTab, drawShape, lensRefs]);

  useLayoutEffect(() => {
    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
    const stopMotion = () => {
      if (!reducedMotion.matches) return;
      animation.current?.cancel();
      animation.current = null;
      if (lensFrameRequest.current !== null) cancelAnimationFrame(lensFrameRequest.current);
      lensFrameRequest.current = null;
      const current = getComputedStyle(pane.current!);
      applyLensFrame({
        left: current.left, top: current.top, width: current.width, height: current.height,
      }, lensRefs);
      drawShape({
        left: parseFloat(current.left), top: parseFloat(current.top),
        width: parseFloat(current.width), height: parseFloat(current.height),
      });
    };
    reducedMotion.addEventListener("change", stopMotion);
    return () => {
      animation.current?.cancel();
      if (lensFrameRequest.current !== null) cancelAnimationFrame(lensFrameRequest.current);
      reducedMotion.removeEventListener("change", stopMotion);
    };
  }, [drawShape, lensRefs]);

  const svgWidth = geometry.tabs.at(-1)!.left + geometry.tabs.at(-1)!.width;

  return (
    <>
      <svg className="profile-tab-glass-unified" aria-hidden="true"
        width={svgWidth} height={geometry.height} overflow="visible">
        <defs>
          <radialGradient ref={topGradient} id={`${gradientId}-top`}
            gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1">
            <stop className="profile-tab-glass-shine-stop profile-tab-glass-shine-top"
              offset="0" stopColor="var(--colour-white)" />
            <stop offset="0.58" stopColor="var(--colour-white)" stopOpacity="0" />
          </radialGradient>
          <radialGradient ref={lowerGradient} id={`${gradientId}-lower`}
            gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1">
            <stop className="profile-tab-glass-shine-stop profile-tab-glass-shine-lower"
              offset="0" stopColor="var(--colour-white)" />
            <stop offset="0.48" stopColor="var(--colour-white)" stopOpacity="0" />
          </radialGradient>
          <linearGradient ref={depthGradient} id={`${gradientId}-depth`}
            gradientUnits="userSpaceOnUse">
            <stop className="profile-tab-glass-shine-stop profile-tab-glass-depth-start"
              offset="0" stopColor="var(--colour-white)" />
            <stop offset="0.36" stopColor="var(--colour-white)" stopOpacity="0" />
            <stop className="profile-tab-glass-shine-stop profile-tab-glass-depth-shade"
              offset="0.72" stopColor="var(--colour-c03)" />
            <stop className="profile-tab-glass-shine-stop profile-tab-glass-depth-end"
              offset="1" stopColor="var(--colour-white)" />
          </linearGradient>
        </defs>
        <g className="profile-tab-glass-material">
          <path ref={surfacePath} className="profile-tab-glass-unified-surface" />
          <path ref={topShinePath} className="profile-tab-glass-unified-layer"
            fill={`url(#${gradientId}-top)`} />
          <path ref={lowerReflectionPath} className="profile-tab-glass-unified-layer"
            fill={`url(#${gradientId}-lower)`} />
          <path ref={depthPath} className="profile-tab-glass-unified-layer"
            fill={`url(#${gradientId}-depth)`} />
        </g>
      </svg>
      <div ref={pane} className="profile-tab-glass" aria-hidden="true"
        style={{
          height: PROFILE_TAB_GLASS_DIAMETER,
          top: (geometry.height - PROFILE_TAB_GLASS_DIAMETER) / 2 + geometry.tabs[activeTab].top,
        }} />
    </>
  );
}
