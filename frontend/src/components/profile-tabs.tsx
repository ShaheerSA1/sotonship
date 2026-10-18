import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ProfileTabGlass, type TabGlassGeometry } from "./profile-tab-glass";
import { createProfileTabLensRefs } from "./profile-tab-lens-refs";
import { ProfileTabRefraction } from "./profile-tab-refraction";
import { ShoppingList } from "./shopping-list";
import { TabIcon } from "./tab-icon";
import { useTabSwipe } from "./use-tab-swipe";
import "./profile-tabs.css";

const tabs = ["overview", "list", "settings"] as const;
export type AppTab = typeof tabs[number];

const descriptions = {
  overview: "An overview of your activity will appear here once the backend is connected.",
  settings: "App preferences will appear here as they are added.",
};

export function ProfileTabs({ activeTab, onTabChange, sampleRequest, actions }: {
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
  sampleRequest: number;
  actions: ReactNode;
}) {
  const activeIndex = tabs.indexOf(activeTab);
  useEffect(() => {
    if (sampleRequest > 0) onTabChange("list");
  }, [sampleRequest, onTabChange]);
  const swipe = useTabSwipe((direction) => {
    onTabChange(tabs[Math.max(0, Math.min(tabs.length - 1, activeIndex + direction))]);
  });
  const id = useId();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const list = useRef<HTMLDivElement | null>(null);
  const [geometry, setGeometry] = useState<TabGlassGeometry | null>(null);
  const lens = useMemo(() => createProfileTabLensRefs(), []);

  useLayoutEffect(() => {
    const element = list.current!;
    const observer = new ResizeObserver(() => {
      const bounds = element.getBoundingClientRect();
      const tabBounds = buttons.current.map((button) => button!.getBoundingClientRect());
      setGeometry({
        height: Math.max(...tabBounds.map((tab) => tab.height)),
        tabs: tabBounds.map((tab) => ({ left: tab.left - bounds.left, width: tab.width, top: tab.top - bounds.top })),
      });
    });
    observer.observe(element);
    buttons.current.forEach((button) => observer.observe(button!));
    return () => observer.disconnect();
  }, []);

  return (
    <section className="profile-tabs" aria-label="App sections" {...swipe}>

      {tabs.map((label, index) => (
        <div
          key={label}
          id={`${id}-panel-${index}`}
          role="tabpanel"
          aria-labelledby={`${id}-tab-${index}`}
          hidden={activeIndex !== index}
          data-panel={label}
          tabIndex={0}
          className="profile-tabs-panel"
        >
          {label === "list" ? (
            <ShoppingList sampleRequest={sampleRequest} />
          ) : (
            <>
              <h2>{label.charAt(0).toUpperCase() + label.slice(1)}</h2>
              <p>{descriptions[label]}</p>
            </>
          )}
        </div>
      ))}
      {actions}
      <div className="profile-tabs-list" role="tablist" aria-label="App sections" ref={list}>
        {geometry && (
          <>
            {/* Lens nodes mount first because the glass layout effect writes into them. */}
            <ProfileTabRefraction geometry={geometry} labels={tabs} lens={lens} />
            <ProfileTabGlass geometry={geometry} activeTab={activeIndex} lensRefs={lens} />
          </>
        )}
        {tabs.map((label, index) => (
          <button
            key={label}
            ref={(button) => { buttons.current[index] = button; }}
            id={`${id}-tab-${index}`}
            type="button"
            data-tab-index={index}
            role="tab"
            aria-label={label}
            title={label.charAt(0).toUpperCase() + label.slice(1)}
            aria-selected={activeIndex === index}
            aria-controls={`${id}-panel-${index}`}
            tabIndex={activeIndex === index ? 0 : -1}
            onClick={() => onTabChange(label)}
            onKeyDown={(event) => {
              let next: number;
              switch (event.key) {
                case "ArrowRight": next = (index + 1) % tabs.length; break;
                case "ArrowLeft": next = (index + tabs.length - 1) % tabs.length; break;
                case "Home": next = 0; break;
                case "End": next = tabs.length - 1; break;
                default: return;
              }
              event.preventDefault();
              onTabChange(tabs[next]);
              buttons.current[next]?.focus();
            }}
          >
            <span style={{ opacity: geometry ? 0 : 1 }}><TabIcon name={label} /></span>
          </button>
        ))}
      </div>
    </section>
  );
}
