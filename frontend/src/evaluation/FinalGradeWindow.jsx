import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { evaluationService } from "@evaluation/evaluationService.js";
import {
  useEnrolmentCatalog,
  useSubjectCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Consulta de resultado: nota final de un estudiante en una subarea (RF-RES-001).
 *
 * La API entrega la nota final redondeada (RF-RES-002); se
 * recalcula ante cualquier corrección mientras el ciclo esté abierto. Una
 * unidad sin nota es "sin calificar", no cero: se distingue con su propia
 * etiqueta y con el conteo de unidades pendientes. La vista presenta
 * final_grade sin repetir el redondeo ni usar el promedio intermedio.
 */
export function FinalGradeWindow({ cycleId, onClose }) {
  const enrolments = useEnrolmentCatalog();
  const subjects = useSubjectCatalog();

  const [enrolmentId, setEnrolmentId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canQuery = enrolmentId !== "" && subjectId !== "";

  const handleQuery = async (event) => {
    event.preventDefault();
    if (!canQuery) return;

    setLoading(true);
    setError("");
    setData(null);
    try {
      const result = await evaluationService.getFinalSubjectGrade(
        cycleId,
        enrolmentId,
        subjectId
      );
      setData(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <FloatingWindow
      description="Nota final de la subárea: promedio de las notas de unidad registradas, redondeado al entero por el sistema."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Consultar resultado"
      width={WINDOW_WIDTH.compact}
    >
      <Stack component="form" gap={2} onSubmit={handleQuery}>
        <FormSelect
          error={enrolments.error}
          fullWidth
          helperText={
            !enrolments.loading && enrolments.options.length === 0
              ? "No hay matriculas vigentes."
              : undefined
          }
          label="Estudiante"
          loading={enrolments.loading}
          onChange={(event) => setEnrolmentId(event.target.value)}
          options={enrolments.options}
          placeholder="Seleccione una matricula"
          value={enrolmentId}
        />
        <FormSelect
          error={subjects.error}
          fullWidth
          helperText={
            !subjects.loading && subjects.options.length === 0
              ? "No hay cursos registrados."
              : undefined
          }
          label="Subarea"
          loading={subjects.loading}
          onChange={(event) => setSubjectId(event.target.value)}
          options={subjects.options}
          placeholder="Seleccione una subarea"
          value={subjectId}
        />
        <Button
          disabled={!canQuery || loading}
          type="submit"
          variant="contained"
        >
          Consultar
        </Button>

        {loading ? <CircularProgress size={24} /> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
        {!loading && !error && data ? (
          <Stack gap={0.5}>
            <Typography variant="h4">
              {data.final_grade != null ? data.final_grade : "Sin calificar"}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {data.graded_units} de {data.total_units} unidades calificadas
              {data.pending_units > 0
                ? ` — ${data.pending_units} pendiente${data.pending_units === 1 ? "" : "s"} de registrar`
                : ""}
            </Typography>
          </Stack>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
