import { useId } from "react";
import { TabIconShape, type TabName } from "./tab-icon";
import { LENS_SLICE_COUNT } from "./profile-tab-lens";
import type { ProfileTabLensRefs } from "./profile-tab-lens-refs";
import type { TabGlassGeometry } from "./profile-tab-glass";

export function ProfileTabRefraction({
  geometry, labels, lens,
}: {
  geometry: TabGlassGeometry;
  labels: readonly TabName[];
  lens: ProfileTabLensRefs;
}) {
  const id = useId();
  const width = Math.max(...geometry.tabs.map((tab) => tab.left + tab.width));
  const icons = labels.map((label, index) => (
    <g key={label} data-tab-index={index}
      transform={`translate(${geometry.tabs[index].left + geometry.tabs[index].width / 2 - 11} ${geometry.height / 2 + geometry.tabs[index].top - 11}) scale(${22 / 24})`}>
      <TabIconShape name={label} />
    </g>
  ));
  return (
    <svg className="profile-tab-labels" width={width} height={geometry.height}
      aria-hidden="true" focusable="false">
      <defs>
        <mask id={`${id}-outside`} maskUnits="userSpaceOnUse"
          x="-8" y="-8" width={width + 16} height={geometry.height + 16}>
          <rect x="-8" y="-8" width={width + 16} height={geometry.height + 16} fill="white" />
          <path ref={lens.outsideLens} fill="rgba(0, 0, 0, 1)" />
        </mask>
        <clipPath id={`${id}-inside`} clipPathUnits="userSpaceOnUse">
          <path ref={lens.insideLens} />
        </clipPath>
        {Array.from({ length: LENS_SLICE_COUNT }, (_, sliceIndex) => (
          <clipPath key={sliceIndex} id={`${id}-slice-${sliceIndex}`}
            clipPathUnits="userSpaceOnUse">
            <rect ref={(element) => { lens.sliceLenses.current[sliceIndex] = element; }} />
          </clipPath>
        ))}
      </defs>
      <g className="profile-tab-labels-normal" mask={`url(#${id}-outside)`}>{icons}</g>
      <g clipPath={`url(#${id}-inside)`} className="profile-tab-labels-magnified">
        {Array.from({ length: LENS_SLICE_COUNT }, (_, sliceIndex) => (
          <g key={sliceIndex} clipPath={`url(#${id}-slice-${sliceIndex})`}>
            <g ref={(element) => { lens.sliceContents.current[sliceIndex] = element; }}>{icons}</g>
          </g>
        ))}
      </g>
    </svg>
  );
}
