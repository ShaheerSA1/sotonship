import { useState } from "react";
import { AppMap } from "./components/app-map";
import { ProfileTabs, type AppTab } from "./components/profile-tabs";

export function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [sampleRequest, setSampleRequest] = useState(0);
  const [activeTab, setActiveTab] = useState<AppTab>("list");
  return (
    <main className="mobile-app" data-theme={darkMode ? "dark" : "light"}>
      <AppMap darkMode={darkMode} minimized={activeTab !== "list"} />
      <ProfileTabs activeTab={activeTab} onTabChange={setActiveTab} sampleRequest={sampleRequest} actions={
        <div className="app-actions" aria-label="List and appearance actions">
          <button type="button" onClick={() => setSampleRequest((current) => current + 1)}
            title="Replace the list with 20 sample shopping items">add items</button>
          <button type="button" aria-pressed={darkMode} onClick={() => setDarkMode((current) => !current)}
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}>switch mode</button>
        </div>
      } />
    </main>
  );
}
