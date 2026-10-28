import { useState } from "react";

// ---- Types: these mirror the Pydantic models in backend/models/batch_model.py ----

type Detected = {
  index: number;                              // position in reading order (0-based)
  box: [number, number, number, number];      // [x1, y1, x2, y2] in pixels of the ORIGINAL photo
  fit: number;                                // 0-1, how rectangular the detected shape was
  card: { name: string; card_number?: string; language?: string }; // Gemini's answer
};

type BatchResult = {
  image_width: number;    // original photo size, needed to turn pixels into percentages
  image_height: number;
  detect_ms: number;      // time spent in OpenCV
  identify_ms: number;    // time spent waiting on Gemini
  cards: Detected[];
};

export function BatchPanel() {
  const [url, setUrl] = useState<string | null>(null);        // local preview of the photo
  const [data, setData] = useState<BatchResult | null>(null); // backend response
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show the photo immediately, and clear any previous result
    setUrl(URL.createObjectURL(file));
    setData(null);
    setError(null);
    setLoading(true);

    // Send the photo to the backend as multipart form data
    const form = new FormData();
    form.append("image", file);
    try {
      const res = await fetch("/api/batch", { method: "POST", body: form });
      if (!res.ok) {
        // FastAPI puts its error message in "detail"
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Batch scan failed with status ${res.status}`);
      }
      setData(await res.json());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <input type="file" accept="image/*" onChange={onFile} />
      {loading && <p>Finding cards with OpenCV, then identifying them with Gemini...</p>}
      {error && <p style={{ color: "#d9534f" }}>{error}</p>}

      {url && (
        <div style={{ position: "relative", marginTop: 16 }}>
          <img src={url} style={{ width: "100%", display: "block" }} />

          {/* Draw one green box per detected card on top of the photo.
              Positions are percentages of the image size, so they stay correct
              however big the photo is displayed. */}
          {data?.cards.map((c) => {
            const [x1, y1, x2, y2] = c.box;
            return (
              <div
                key={c.index}
                style={{
                  position: "absolute",
                  border: "3px solid #22c55e",
                  left: `${(x1 / data.image_width) * 100}%`,
                  top: `${(y1 / data.image_height) * 100}%`,
                  width: `${((x2 - x1) / data.image_width) * 100}%`,
                  height: `${((y2 - y1) / data.image_height) * 100}%`,
                }}
              >
                <span style={{ background: "#22c55e", color: "#000", fontSize: 12, padding: "0 4px" }}>
                  {c.index + 1}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Timing summary and the table of coordinates + identified cards */}
      {data && (
        <>
          <p>
            OpenCV: {data.detect_ms} ms · Gemini: {data.identify_ms} ms · {data.cards.length} cards
          </p>
          <table style={{ width: "100%", fontSize: 14 }}>
            <thead>
              <tr><th>#</th><th>Card</th><th>No.</th><th>Box (x1,y1,x2,y2)</th><th>Fit</th></tr>
            </thead>
            <tbody>
              {data.cards.map((c) => (
                <tr key={c.index}>
                  <td>{c.index + 1}</td>
                  <td>{c.card.name}</td>
                  <td>{c.card.card_number}</td>
                  <td>{c.box.map(Math.round).join(", ")}</td>
                  <td>{c.fit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}