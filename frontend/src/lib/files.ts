import { api } from "./api";

/**
 * Opens a PDF (or any file) served from an authenticated API route in a
 * new tab. A plain `<a href target="_blank">` can't work here -- the
 * browser only attaches our JWT bearer token on requests made through
 * axios (see api.ts's interceptor), never on a native navigation/anchor
 * click, so a direct link 401s with "Not authenticated". Fetching the
 * bytes ourselves (with the token attached) and handing the browser a
 * blob: URL sidesteps that.
 *
 * Uses a programmatic <a> click rather than window.open(blobUrl) --
 * recent Chromium versions silently fail to navigate a *new* window
 * directly to a blob: URL (a security restriction on blob same-origin
 * access across browsing contexts), while a user-gesture anchor click
 * with target="_blank" is still honored.
 */
export async function openAuthenticatedFile(url: string): Promise<void> {
  const response = await api.get(url, { responseType: "blob" });
  const blobUrl = URL.createObjectURL(response.data as Blob);

  const link = document.createElement("a");
  link.href = blobUrl;
  link.target = "_blank";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}
