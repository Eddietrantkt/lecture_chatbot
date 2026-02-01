

  import { createRoot } from "react-dom/client";
  import App from "./App.tsx";
  import "./index.css";

  // ✅ Debug logging
  console.log('%c[FRONTEND] Starting app...', 'color: cyan; font-weight: bold;');
  console.log('Hostname:', window.location.hostname);
  console.log('Port:', window.location.port);
  console.log('VITE_API_URL:', import.meta.env.VITE_API_URL);

  createRoot(document.getElementById("root")!).render(<App />);
    