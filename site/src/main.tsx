import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./index.css";

import Home from "./pages/Home";
import GoalPage from "./pages/Goal";
import Start from "./pages/Start";

/**
 * Hash routes, so every address is index.html plus a fragment: a refresh or a
 * shared link never depends on the host rewriting paths.
 */
const ROUTES: Record<string, () => React.JSX.Element> = {
  "/": Home,
  "/goal": GoalPage,
  "/start": Start,
};

/** "#/goal?id=x" is /goal, and "#/#how" is the home page scrolled to a section. */
function currentPath(): string {
  const hash = window.location.hash.replace(/^#/, "");
  return hash.split("?")[0].split("#")[0] || "/";
}

function App() {
  const [path, setPath] = useState(currentPath);
  const [address, setAddress] = useState(() => window.location.hash);
  useEffect(() => {
    const onHash = () => {
      setPath(currentPath());
      setAddress(window.location.hash);
      if (!window.location.hash.includes("#how") && !window.location.hash.includes("#goals")) window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const Page = ROUTES[path] ?? Home;
  // Keyed by the whole address, so a page reading ?id= starts over when only
  // that part changes, instead of showing what the previous link asked for.
  return <Page key={address} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
