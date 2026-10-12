import { useEffect, useState } from "react";

import CenterFocusStrongOutlinedIcon from "@mui/icons-material/CenterFocusStrongOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  CAMERA_ERROR,
  CAMERA_ERROR_MESSAGES,
  CameraAccessError,
  createCameraSession,
} from "@shared/platform/camera.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

export function CameraPreviewWindow({
  onClose,
  requestSession = createCameraSession,
}) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState({ status: "loading" });

  useEffect(() => {
    let disposed = false;
    let session;

    requestSession()
      .then((nextSession) => {
        session = nextSession;
        if (disposed) {
          nextSession.stop();
          return;
        }
        setResult({ status: "active", session: nextSession });
      })
      .catch((error) => {
        if (disposed) return;
        const code =
          error instanceof CameraAccessError
            ? error.code
            : CAMERA_ERROR.unavailable;
        setResult({ status: "error", code });
      });

    return () => {
      disposed = true;
      session?.stop();
    };
  }, [attempt, requestSession]);

  const retry = () => {
    setResult({ status: "loading" });
    setAttempt((current) => current + 1);
  };

  return (
    <FloatingWindow
      busy={result.status === "loading"}
      description="Comprueba el encuadre antes de iniciar una lectura. Si la imagen queda borrosa, usa Reenfocar cámara para reiniciar el autoenfoque sin cerrar esta vista."
      footer={
        <>
          {result.status === "error" ? (
            <Button onClick={retry} variant="contained">
              Reintentar
            </Button>
          ) : null}
          {result.status === "active" ? (
            <Button
              onClick={retry}
              startIcon={<CenterFocusStrongOutlinedIcon />}
              variant="outlined"
            >
              Reenfocar cámara
            </Button>
          ) : null}
          <Button onClick={onClose} variant="text">
            Cerrar
          </Button>
        </>
      }
      onClose={onClose}
      open
      title="Vista previa de camara"
      width={WINDOW_WIDTH.medium}
    >
      {result.status === "loading" ? (
        <Stack
          alignItems="center"
          aria-live="polite"
          gap={1.5}
          role="status"
          sx={{ py: 6 }}
        >
          <CircularProgress size={32} />
          <Typography color="text.secondary" variant="body2">
            Solicitando acceso a la camara…
          </Typography>
        </Stack>
      ) : null}

      {result.status === "error" ? (
        <Alert role="alert" severity="warning">
          {CAMERA_ERROR_MESSAGES[result.code] ??
            CAMERA_ERROR_MESSAGES[CAMERA_ERROR.unavailable]}
        </Alert>
      ) : null}

      {result.status === "active" ? (
        <Box
          aria-label="Vista previa en vivo de la camara"
          autoPlay
          component="video"
          muted
          playsInline
          ref={(video) => {
            if (video) video.srcObject = result.session.stream;
          }}
          sx={{
            bgcolor: "common.black",
            borderRadius: 1,
            display: "block",
            maxHeight: "60dvh",
            objectFit: "contain",
            width: "100%",
          }}
        />
      ) : null}
    </FloatingWindow>
  );
}
