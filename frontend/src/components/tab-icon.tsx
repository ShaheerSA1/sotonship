export type TabName = "overview" | "list" | "settings";

const paths: Record<TabName, string> = {
  overview: "M3 10 12 3l9 7M5 9v11h5v-6h4v6h5V9",
  list: "m3 6 1.5 1.5L7 5M10 6h11M3 12l1.5 1.5L7 11M10 12h11M3 18l1.5 1.5L7 17M10 18h11",
  settings: "m9 3-.5 2-2 1-2-.5-2 3.5L4 10.5v3L2.5 15l2 3.5 2-.5 2 1 .5 2h4l.5-2 2-1 2 .5 2-3.5-1.5-1.5v-3L20 9l-2-3.5-2 .5-2-1-.5-2Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
};

export function TabIconShape({ name }: { name: TabName }) {
  return <path d={paths[name]} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />;
}

export function TabIcon({ name }: { name: TabName }) {
  return <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><TabIconShape name={name} /></svg>;
}
