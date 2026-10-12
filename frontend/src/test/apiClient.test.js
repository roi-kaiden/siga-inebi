import { apiClient } from "@shared/api/apiClient.js";
import { vi } from "vitest";

describe("apiClient", () => {
  test("includes credentials in requests", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    await apiClient.get("/health/");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/health/",
      expect.objectContaining({ credentials: "include" })
    );
  });

  test("sends csrf token on write requests", async () => {
    document.cookie = "csrftoken=test-token";
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    await apiClient.post("/auth/login/", {
      username: "admin",
      password: "admin",
    });

    const [, options] = globalThis.fetch.mock.calls[0];
    expect(options.headers.get("X-CSRFToken")).toBe("test-token");
  });

  test("sends patch requests with a json body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ name: "Sede Central" }),
    });

    await apiClient.patch("/academics/campuses/abc/", { name: "Sede Central" });

    const [url, options] = globalThis.fetch.mock.calls[0];
    expect(url).toBe("/api/v1/academics/campuses/abc/");
    expect(options.method).toBe("PATCH");
    expect(options.body).toBe(JSON.stringify({ name: "Sede Central" }));
    expect(options.headers.get("Content-Type")).toBe("application/json");
  });

  test("resolves delete requests that answer 204 without a body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      headers: new Headers(),
      json: async () => {
        throw new Error("no body");
      },
    });

    await expect(apiClient.del("/academics/campuses/abc/")).resolves.toBeNull();

    const [url, options] = globalThis.fetch.mock.calls[0];
    expect(url).toBe("/api/v1/academics/campuses/abc/");
    expect(options.method).toBe("DELETE");
    expect(options.body).toBeUndefined();
  });

  test("surfaces a permission rejection sent as plain text", async () => {
    // Las vistas de permisos responden `{error: "texto"}`, no `{error:{detail}}`.
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: "Solo los docentes registran notas." }),
    });

    await expect(apiClient.post("/grades/", {})).rejects.toThrow(
      "Solo los docentes registran notas."
    );
  });

  test("surfaces the first field error reported by the serializer", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ value: ["La nota debe estar entre 0 y 100."] }),
    });

    await expect(apiClient.post("/grades/", {})).rejects.toThrow(
      "La nota debe estar entre 0 y 100."
    );
  });

  test("surfaces domain errors raised by a delete", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({
        error: { detail: "La sede tiene jornadas en un ciclo abierto." },
      }),
    });

    await expect(
      apiClient.del("/academics/campuses/abc/")
    ).rejects.toMatchObject({
      status: 400,
      message: "La sede tiene jornadas en un ciclo abierto.",
    });
  });

  test("handles 401 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "No autenticado." }),
    });

    await expect(apiClient.get("/auth/me/")).rejects.toMatchObject({
      status: 401,
      message: "No autenticado.",
    });
  });

  test("notifies the application when the backend expires a session", async () => {
    const onExpired = vi.fn();
    window.addEventListener("siga:session-expired", onExpired);
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({
        "content-type": "application/json",
        "X-SIGA-Session-Expired": "1",
      }),
      json: async () => ({
        error: { detail: "La sesión expiró por inactividad." },
      }),
    });

    await expect(apiClient.get("/students/")).rejects.toThrow(
      "La sesión expiró por inactividad."
    );

    expect(onExpired).toHaveBeenCalledTimes(1);
    window.removeEventListener("siga:session-expired", onExpired);
  });

  test("handles 403 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "Sin permiso." }),
    });

    await expect(apiClient.get("/auth/me/")).rejects.toMatchObject({
      status: 403,
      message: "Sin permiso.",
    });
  });

  test("handles validation responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: { detail: "Datos invalidos." } }),
    });

    await expect(apiClient.post("/auth/login/", {})).rejects.toMatchObject({
      status: 422,
      message: "Datos invalidos.",
    });
  });

  test("handles server responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "Error interno." }),
    });

    await expect(apiClient.get("/health/")).rejects.toMatchObject({
      status: 500,
      message: "Error interno.",
    });
  });

  test.each(["Failed to fetch", "NetworkError when attempting to fetch resource."])(
    "explains a network failure in Spanish and permits a retry (%s)",
    async (browserMessage) => {
      globalThis.fetch = vi
        .fn()
        .mockRejectedValueOnce(new TypeError(browserMessage))
        .mockResolvedValueOnce({
          ok: true,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({ final_grade: null }),
        });

      await expect(apiClient.get("/results/")).rejects.toThrow(
        "No se pudo conectar con el servidor. Verifica tu conexión y vuelve a intentarlo."
      );
      await expect(apiClient.get("/results/")).resolves.toEqual({ final_grade: null });
      expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    }
  );

  test("sends FormData bodies as-is without a Content-Type header", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    const formData = new FormData();
    formData.append("photo", new File(["data"], "photo.jpg"));

    await apiClient.patch("/students/1/", formData);

    const [, options] = globalThis.fetch.mock.calls[0];
    expect(options.body).toBe(formData);
    expect(options.headers.has("Content-Type")).toBe(false);
  });

  test("patch sends the PATCH method and csrf header", async () => {
    document.cookie = "csrftoken=test-token";
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    await apiClient.patch("/students/1/", new FormData());

    const [, options] = globalThis.fetch.mock.calls[0];
    expect(options.method).toBe("PATCH");
    expect(options.headers.get("X-CSRFToken")).toBe("test-token");
  });
});
