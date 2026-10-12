import { useState } from "react";

import PreviewOutlinedIcon from "@mui/icons-material/PreviewOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { useSectionCatalog } from "@shared/catalogs/academicCatalogs.js";
import { todayInputValue } from "@shared/utils/format.js";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

function ClosureSummary({ result }) {
  return (
    <Stack gap={1.25}>
      <Typography variant="subtitle2">
        {result.grade_name} - cierre del {result.event_date}
      </Typography>
      <Stack direction="row" flexWrap="wrap" gap={1}>
        <StatusChip
          label={`${result.included.length} por cerrar`}
          variant="success"
        />
        <StatusChip
          label={`${result.omitted.length} omitidos`}
          variant="warning"
        />
        {result.is_covering ? (
          <StatusChip label="Docente de cobertura" variant="primary" />
        ) : null}
      </Stack>
      {result.omitted.length ? (
        <Typography color="text.secondary" variant="body2">
          Las omisiones se conservan sin crear movimientos: el estudiante ya
          tiene salida o no tiene ingreso registrado.
        </Typography>
      ) : null}
    </Stack>
  );
}

/** The UI presents the result; authorization and audit remain in the backend. */
export function SectionClosureWindow({
  onClose,
  onClosed,
  previewClosure,
  submitClosure,
}) {
  const sections = useSectionCatalog();
  const [sectionId, setSectionId] = useState("");
  const [eventDate, setEventDate] = useState(todayInputValue);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmingCoverage, setConfirmingCoverage] = useState(false);
  const [completed, setCompleted] = useState(false);

  const canPreview = sectionId !== "" && eventDate !== "";
  const payload = { section_id: sectionId, event_date: eventDate };

  const preview = async (event) => {
    event.preventDefault();
    if (!canPreview) return;
    setBusy(true);
    setError("");
    setCompleted(false);
    try {
      setResult(await previewClosure(payload));
    } catch (requestError) {
      setError(requestError.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const closeSection = async (confirmed = false) => {
    setBusy(true);
    setError("");
    try {
      const response = await submitClosure({
        ...payload,
        confirmed,
      });
      setResult(response);
      if (response.confirmation_required) {
        setConfirmingCoverage(true);
        return;
      }
      setCompleted(true);
      onClosed();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <FloatingWindow
        description="Revise a quienes se declarara salida antes de confirmar. La cobertura exige una segunda confirmacion y queda auditada."
        footer={
          <Stack direction="row" gap={1}>
            <Button disabled={busy} onClick={onClose} variant="text">
              Cerrar
            </Button>
            {result ? (
              <Button
                disabled={busy || completed}
                onClick={() => closeSection()}
                variant="contained"
              >
                {completed ? "Cierre registrado" : "Declarar cierre"}
              </Button>
            ) : null}
          </Stack>
        }
        onClose={busy ? undefined : onClose}
        open
        title="Cierre declarado por seccion"
        width={WINDOW_WIDTH.medium}
      >
        <Stack gap={2.5}>
          <Box component="form" onSubmit={preview}>
            <Stack gap={2}>
              <FormSelect
                error={sections.error}
                fullWidth
                helperText={
                  !sections.loading && !sections.options.length
                    ? "No hay secciones registradas."
                    : undefined
                }
                label="Seccion"
                loading={sections.loading}
                onChange={(event) => {
                  setSectionId(event.target.value);
                  setResult(null);
                  setCompleted(false);
                }}
                options={sections.options}
                placeholder="Seleccione una seccion"
                required
                value={sectionId}
              />
              <DateField
                fullWidth
                label="Fecha del cierre"
                onChange={(event) => {
                  setEventDate(event.target.value);
                  setResult(null);
                  setCompleted(false);
                }}
                required
                value={eventDate}
              />
              <Box>
                <Button
                  disabled={!canPreview || busy}
                  startIcon={<PreviewOutlinedIcon />}
                  type="submit"
                  variant="outlined"
                >
                  Previsualizar cierre
                </Button>
              </Box>
            </Stack>
          </Box>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {completed ? (
            <Alert severity="success">
              El cierre se registro y quedo en auditoria.
            </Alert>
          ) : null}
          {result ? (
            <>
              <Divider />
              <ClosureSummary result={result} />
            </>
          ) : null}
        </Stack>
      </FloatingWindow>
      <ConfirmDialog
        busy={busy}
        confirmText="Confirmar cierre"
        message={
          result
            ? `Actuara como docente de cobertura para ${result.grade_name}. Se declararan ${result.included.length} salidas y la accion quedara auditada.`
            : "Confirme el cierre por cobertura."
        }
        onClose={() => setConfirmingCoverage(false)}
        onConfirm={() => {
          setConfirmingCoverage(false);
          closeSection(true);
        }}
        open={confirmingCoverage}
        title="Confirmar cierre por cobertura"
      />
    </>
  );
}
