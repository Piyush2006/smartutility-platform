import { AxiosError } from "axios";

/**
 * FastAPI error shape is either {detail: string} (HTTPException) or
 * {detail: [{loc, msg, type}, ...]} (pydantic validation errors). Surface
 * the real message instead of a generic "could not save".
 */
export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          const field = Array.isArray(d?.loc) ? d.loc.filter((p: unknown) => p !== "body").join(".") : null;
          return field ? `${field}: ${d.msg}` : d.msg;
        })
        .filter(Boolean)
        .join("; ");
    }
    if (error.response?.status === 0 || error.code === "ERR_NETWORK") {
      return "Could not reach the server. Check your connection and try again.";
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
