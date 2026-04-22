const LOCAL_BACKEND_URL = "http://localhost:7860";

function sanitizeApiBase(rawUrl?: string): string {
  if (!rawUrl) {
    return "";
  }

  return rawUrl
    .trim()
    .replace("http://0.0.0.0:", "http://localhost:")
    .replace("https://0.0.0.0:", "https://localhost:")
    .replace(/\/$/, "");
}

export function getApiBase(): string {
  const envUrl = sanitizeApiBase(import.meta.env.VITE_API_URL as string | undefined);
  if (envUrl) {
    return envUrl;
  }

  return LOCAL_BACKEND_URL;
}
