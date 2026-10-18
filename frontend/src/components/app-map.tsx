import { useEffect, useRef, useState } from "react";
import { loadMapRuntime, type GeographicMap } from "./map-runtime";
import { CIVIC_CENTRE, zoomForHorizontalSpan } from "./map-camera";
import { createMapStyle, type MapStyle } from "./map-style";
import { attachShopHighlights } from "./map-shop-highlights";
import { shopVectorSource } from "./map-shops";
import "./app-map.css";

export function AppMap({ darkMode, minimized }: { darkMode: boolean; minimized: boolean }) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<GeographicMap | null>(null);
  const base = useRef<MapStyle | null>(null);
  const theme = useRef(darkMode);
  theme.current = darkMode;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const host = container.current!;
    const abort = new AbortController();
    let disposed = false;
    let observer: ResizeObserver | null = null;
    let detachHighlights: (() => void) | null = null;
    loadMapRuntime(abort.signal).then(({ runtime, base: providerStyle }) => {
      if (disposed) return;
      base.current = providerStyle;
      let previousWidth = host.clientWidth;
      const metreScale = runtime.MercatorCoordinate.fromLngLat(CIVIC_CENTRE).meterInMercatorCoordinateUnits();
      const initialZoom = zoomForHorizontalSpan(previousWidth, metreScale);
      const instance = new runtime.Map({
        container: host,
        style: createMapStyle(providerStyle, host, theme.current),
        center: CIVIC_CENTRE,
        zoom: initialZoom,
        bearing: 0,
        pitch: 0,
        minZoom: 9,
        maxZoom: 20,
        // Classify complete native footprints, not zoom-dependent tile fragments.
        zoomLevelsToOverscale: undefined,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        renderWorldCopies: false,
      });
      map.current = instance;
      detachHighlights = attachShopHighlights(instance, shopVectorSource(providerStyle), (failure) => {
        if (disposed) return;
        console.error("[shop building highlights]", failure);
        setLoading(false);
        setError(failure.message);
      });
      instance.on("load", () => { if (!disposed) setLoading(false); });
      instance.on("error", (event) => {
        const failure = event.error;
        if (disposed) return;
        console.error("[Southampton map]", {
          message: failure.message, url: failure.url, status: failure.status, sourceId: event.sourceId,
        });
        setLoading(false);
        setError(`${failure.message}${failure.url ? ` (${failure.url})` : ""}`);
      });
      observer = new ResizeObserver(() => {
        const width = host.clientWidth;
        if (width <= 0) return;
        instance.resize();
        // Preserve the geographic span if the phone preview changes width.
        if (width !== previousWidth) {
          instance.jumpTo({ zoom: instance.getZoom() + Math.log2(width / previousWidth) });
          previousWidth = width;
        }
      });
      observer.observe(host);
    }).catch((failure: Error) => {
      if (disposed) return;
      console.error("[Southampton map]", failure);
      setLoading(false);
      setError(failure.message);
    });
    return () => {
      disposed = true;
      abort.abort();
      observer?.disconnect();
      detachHighlights?.();
      map.current?.remove();
      map.current = null;
      base.current = null;
    };
  }, []);

  useEffect(() => {
    if (map.current && base.current && container.current) {
      map.current.setStyle(createMapStyle(base.current, container.current, darkMode));
    }
  }, [darkMode]);

  return (
    <section className="app-map" data-minimized={minimized} aria-hidden={minimized} inert={minimized}
      aria-label="Map centred on Southampton Civic Centre, initially spanning 500 metres horizontally">
      <div ref={container} className="map-canvas" />
      {loading && !error && <p className="map-status" role="status">Loading Southampton map...</p>}
      {error && <p className="map-status map-error" role="alert">Map could not load: {error}</p>}
    </section>
  );
}
