// Nostobon Android app. A thin native shell that loads the web app from the FastAPI server,
// so web changes in app/static/ show up on the phone without rebuilding the APK.
//
// NOSTOBON_URL picks the server. Default is http://localhost:8000, which reaches the laptop
// over USB through `adb reverse` (see `npm run reverse`). Use an https URL for a hosted build.
const url = process.env.NOSTOBON_URL || "http://localhost:8000";

/** @type {import('@capacitor/cli').CapacitorConfig} */
module.exports = {
  appId: "uk.sotonship.nostobon",
  appName: "Nostobon",
  // Only holds the offline page. The real app is served by the backend.
  webDir: "www",
  backgroundColor: "#f5f4ef",
  server: {
    url,
    cleartext: url.startsWith("http://"),
    errorPath: "offline.html",
  },
  android: {
    // Lets you inspect the WebView from chrome://inspect on the laptop.
    webContentsDebuggingEnabled: true,
  },
};
