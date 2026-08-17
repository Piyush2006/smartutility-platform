import { getErrorMessage } from "@/lib/errors";

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{getErrorMessage(error)}</p>;
}
