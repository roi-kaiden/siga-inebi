import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { CameraPreviewWindow } from "@ui/display/CameraPreviewWindow.jsx";
import { CAMERA_ERROR, CameraAccessError } from "@shared/platform/camera.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

describe("CameraPreviewWindow", () => {
  test("shows the live preview and releases the session when closed", async () => {
    const user = userEvent.setup();
    const stream = { id: "camera-stream" };
    const stop = vi.fn();
    const onClose = vi.fn();
    const { unmount } = renderWithRouter(
      <CameraPreviewWindow
        onClose={onClose}
        requestSession={() => Promise.resolve({ stream, stop })}
      />
    );

    const video = await screen.findByLabelText(
      "Vista previa en vivo de la camara"
    );
    expect(video).toHaveAttribute("playsinline");
    expect(video.srcObject).toBe(stream);

    await user.click(screen.getAllByRole("button", { name: "Cerrar" })[1]);
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    // The parent owns unmounting after onClose, as AttendancePage does.
    unmount();
    expect(stop).toHaveBeenCalledOnce();
  });

  test("explains permission denial and retries without leaking tracks", async () => {
    const user = userEvent.setup();
    const stop = vi.fn();
    const requestSession = vi
      .fn()
      .mockRejectedValueOnce(
        new CameraAccessError(CAMERA_ERROR.permissionDenied)
      )
      .mockResolvedValueOnce({ stream: {}, stop });
    const { unmount } = renderWithRouter(
      <CameraPreviewWindow onClose={vi.fn()} requestSession={requestSession} />
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Habilita el permiso/
    );
    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(
      await screen.findByLabelText("Vista previa en vivo de la camara")
    ).toBeInTheDocument();
    expect(requestSession).toHaveBeenCalledTimes(2);
    unmount();
    expect(stop).toHaveBeenCalledOnce();
  });

  test("restarts the session to request autofocus again", async () => {
    const user = userEvent.setup();
    const firstStop = vi.fn();
    const secondStop = vi.fn();
    const requestSession = vi
      .fn()
      .mockResolvedValueOnce({ stream: { id: "first" }, stop: firstStop })
      .mockResolvedValueOnce({ stream: { id: "second" }, stop: secondStop });
    const { unmount } = renderWithRouter(
      <CameraPreviewWindow onClose={vi.fn()} requestSession={requestSession} />
    );

    await screen.findByLabelText("Vista previa en vivo de la camara");
    await user.click(screen.getByRole("button", { name: "Reenfocar cámara" }));

    await waitFor(() => expect(requestSession).toHaveBeenCalledTimes(2));
    expect(firstStop).toHaveBeenCalledOnce();

    unmount();
    expect(secondStop).toHaveBeenCalledOnce();
  });

  test.each([
    [CAMERA_ERROR.insecure, /conexion segura/],
    [CAMERA_ERROR.unsupported, /no admite/],
    [CAMERA_ERROR.unavailable, /No hay una camara disponible/],
  ])("shows an actionable %s state", async (code, message) => {
    renderWithRouter(
      <CameraPreviewWindow
        onClose={vi.fn()}
        requestSession={() => Promise.reject(new CameraAccessError(code))}
      />
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(
      screen.getByRole("button", { name: "Reintentar" })
    ).toBeInTheDocument();
  });
});
