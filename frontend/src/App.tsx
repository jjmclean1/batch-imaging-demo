import { BatchPanel } from "./components/BatchPanel";
import "./App.css";

// The whole app is one page: a header and the batch scanner.
export default function App() {
  return (
    <main style={{ padding: "2rem", maxWidth: "700px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <header style={{ marginBottom: "2rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>Pokémon Batch Scan Demo</h1>
        <p style={{ color: "#666" }}>
          Upload one photo of several cards. OpenCV splits it up, Gemini identifies them all at once.
        </p>
      </header>

      <BatchPanel />
    </main>
  );
}