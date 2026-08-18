/**
 * Copie d'un graphique SVG (diagramme de capacité, spectre…) vers le
 * presse-papiers sous forme d'image PNG, pour collage direct dans Word.
 *
 * Word ne sait pas coller un <svg> depuis le presse-papiers : il faut lui
 * fournir un bitmap. On sérialise donc le SVG, on le rastérise dans un
 * <canvas> puis on écrit un ClipboardItem image/png.
 *
 * Web uniquement — sur mobile, `copyDiagramImage` retourne false et
 * l'appelant doit se rabattre sur le PDF.
 */

import { Platform } from "react-native";

/** Marge blanche autour du graphique dans l'image exportée [px]. */
const PADDING = 12;
/** Facteur de suréchantillonnage (rendu net dans Word). */
const SCALE = 2;

export type CopyDiagramResult =
  | { ok: true }
  | { ok: false; reason: "unsupported" | "not-found" | "failed" };

/**
 * Trouve le premier <svg> à l'intérieur d'un conteneur repéré par son
 * `data-testid`, le rastérise et le place dans le presse-papiers.
 */
export async function copyDiagramImage(
  containerTestId: string,
  backgroundColor = "#ffffff",
): Promise<CopyDiagramResult> {
  if (Platform.OS !== "web" || typeof document === "undefined") {
    return { ok: false, reason: "unsupported" };
  }

  const container = document.querySelector(
    `[data-testid="${containerTestId}"]`,
  );
  const svg = container?.querySelector("svg");
  if (!svg) return { ok: false, reason: "not-found" };

  try {
    const rect = svg.getBoundingClientRect();
    const w = Math.ceil(rect.width) || 600;
    const h = Math.ceil(rect.height) || 320;

    // Clone + dimensions explicites : sans width/height en dur, certains
    // navigateurs rasterisent une image de taille nulle.
    const clone = svg.cloneNode(true) as SVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));
    if (!clone.getAttribute("viewBox")) {
      clone.setAttribute("viewBox", `0 0 ${w} ${h}`);
    }

    const svgText = new XMLSerializer().serializeToString(clone);
    const svgUrl =
      "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgText);

    const img = new Image();
    img.crossOrigin = "anonymous";
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("SVG image decode failed"));
      img.src = svgUrl;
    });

    const canvas = document.createElement("canvas");
    canvas.width = (w + PADDING * 2) * SCALE;
    canvas.height = (h + PADDING * 2) * SCALE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return { ok: false, reason: "failed" };

    ctx.scale(SCALE, SCALE);
    // Fond opaque : un PNG transparent devient noir dans Word.
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, w + PADDING * 2, h + PADDING * 2);
    ctx.drawImage(img, PADDING, PADDING, w, h);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), "image/png"),
    );
    if (!blob) return { ok: false, reason: "failed" };

    const w2 = window as unknown as {
      ClipboardItem?: new (items: Record<string, Blob>) => unknown;
    };
    if (!navigator.clipboard || !w2.ClipboardItem) {
      return { ok: false, reason: "unsupported" };
    }
    const ClipboardItemCtor = w2.ClipboardItem;
    await (
      navigator.clipboard as unknown as {
        write: (data: unknown[]) => Promise<void>;
      }
    ).write([new ClipboardItemCtor({ "image/png": blob })]);

    return { ok: true };
  } catch {
    return { ok: false, reason: "failed" };
  }
}

/** Télécharge le graphique en PNG — repli quand le presse-papiers est refusé. */
export async function downloadDiagramImage(
  containerTestId: string,
  filename = "diagramme.png",
  backgroundColor = "#ffffff",
): Promise<boolean> {
  if (Platform.OS !== "web" || typeof document === "undefined") return false;
  const container = document.querySelector(
    `[data-testid="${containerTestId}"]`,
  );
  const svg = container?.querySelector("svg");
  if (!svg) return false;

  try {
    const rect = svg.getBoundingClientRect();
    const w = Math.ceil(rect.width) || 600;
    const h = Math.ceil(rect.height) || 320;
    const clone = svg.cloneNode(true) as SVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));
    const svgText = new XMLSerializer().serializeToString(clone);
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("decode failed"));
      img.src =
        "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgText);
    });
    const canvas = document.createElement("canvas");
    canvas.width = (w + PADDING * 2) * SCALE;
    canvas.height = (h + PADDING * 2) * SCALE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;
    ctx.scale(SCALE, SCALE);
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, w + PADDING * 2, h + PADDING * 2);
    ctx.drawImage(img, PADDING, PADDING, w, h);

    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = filename;
    a.click();
    return true;
  } catch {
    return false;
  }
}
