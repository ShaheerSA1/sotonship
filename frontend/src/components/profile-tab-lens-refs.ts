import { createRef, type RefObject } from "react";

export type ProfileTabLensRefs = {
  insideLens: RefObject<SVGPathElement | null>;
  outsideLens: RefObject<SVGPathElement | null>;
  sliceLenses: RefObject<(SVGRectElement | null)[]>;
  sliceContents: RefObject<(SVGGElement | null)[]>;
};

export function createProfileTabLensRefs(): ProfileTabLensRefs {
  return {
    insideLens: createRef<SVGPathElement>(),
    outsideLens: createRef<SVGPathElement>(),
    sliceLenses: { current: [] },
    sliceContents: { current: [] },
  };
}
