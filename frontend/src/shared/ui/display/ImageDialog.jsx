import { useId } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";

/**
 * Visor de imagen a pantalla grande (fotografia de expediente).
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {string}   props.src
 * @param {string}  [props.alt]
 * @param {string}  [props.downloadName]
 * @param {Function} props.onClose
 */
export function ImageDialog({ alt = "", downloadName, onClose, open, src }) {
  const titleId = useId();
  const title = alt ? `Foto de ${alt}` : "Imagen";

  return (
    // El dialogo se nombra "Foto de X" y no solo "X": en la misma pantalla puede
    // haber abierta la ventana de detalle de la misma persona, y dos dialogos con
    // el mismo nombre son indistinguibles para un lector de pantalla.
    //
    // Se usa `aria-labelledby` y no `aria-label`: MUI reenvia el primero al nodo
    // con role="dialog" y el segundo se queda en el contenedor de presentacion,
    // donde ninguna tecnologia asistiva lo lee como nombre del dialogo.
    <Dialog
      aria-labelledby={titleId}
      maxWidth="md"
      onClose={onClose}
      open={open}
    >
      <Stack
        alignItems="center"
        direction="row"
        gap={1}
        sx={{ p: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Typography
          id={titleId}
          sx={{ fontSize: "0.875rem", fontWeight: 600, mr: "auto", pl: 0.5 }}
        >
          {title}
        </Typography>
        <Button
          component="a"
          download={downloadName || "foto"}
          href={src || undefined}
          size="small"
          startIcon={<DownloadIcon fontSize="small" />}
          variant="text"
        >
          Descargar
        </Button>
        <IconButton aria-label="Cerrar imagen" onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Box
        alt={alt}
        component="img"
        src={src || undefined}
        sx={{
          display: "block",
          maxWidth: "100%",
          maxHeight: "75dvh",
          objectFit: "contain",
          bgcolor: "background.default",
        }}
      />
    </Dialog>
  );
}
