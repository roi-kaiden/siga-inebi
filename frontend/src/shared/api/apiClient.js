const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

function getErrorMessage(detail) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return (
      detail.find((item) => typeof item === "string") ||
      "Solicitud no completada."
    );
  }

  if (detail && typeof detail === "object") {
    const nested =
      detail.non_field_errors || detail.detail || Object.values(detail)[0];
    return getErrorMessage(nested);
  }

  return "Solicitud no completada.";
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    if (response.headers.get("X-SIGA-Session-Expired") === "1") {
      window.dispatchEvent(new Event("siga:session-expired"));
    }
    // El backend responde de tres formas segun la capa que rechaza: la de
    // dominio manda `{error: {detail}}`, las vistas de permisos mandan
    // `{error: "texto"}` y DRF manda los errores por campo (`{campo: [...]}`).
    // Sin la segunda y la tercera, un 403 explicado o un campo invalido se leian
    // como "Solicitud no completada.", que no le dice a nadie que corregir.
    const detail = data?.error?.detail ?? data?.error ?? data?.detail ?? data;
    const message = getErrorMessage(detail);
    const error = new Error(message);
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

function getCookie(name) {
  const value = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`))
    ?.split("=")[1];
  return value ? decodeURIComponent(value) : "";
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  const isFormData = options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const method = (options.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      method,
      credentials: "include",
      headers,
      body: options.body
        ? isFormData
          ? options.body
          : JSON.stringify(options.body)
        : undefined,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "No se pudo conectar con el servidor. Verifica tu conexión y vuelve a intentarlo.",
        { cause: error }
      );
    }
    throw error;
  }

  return parseResponse(response);
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  del: (path) => request(path, { method: "DELETE" }),
};
