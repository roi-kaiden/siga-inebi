import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import PhotoCameraOutlinedIcon from "@mui/icons-material/PhotoCameraOutlined";
import QrCodeScannerOutlinedIcon from "@mui/icons-material/QrCodeScannerOutlined";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";

import {
  ATTENDANCE_ALERT_LABEL,
  ATTENDANCE_ALERT_VARIANT,
  attendanceService,
  MOVEMENT_LABEL,
  MOVEMENT_VARIANT,
  ORIGIN_LABEL,
  ORIGIN_VARIANT,
  TRANSMISSION_LABEL,
} from "@attendance/attendanceService.js";
import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  labelIndex,
  useSectionCatalog,
  useShiftCatalog,
  useStudentCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import {
  CAMERA_ERROR_MESSAGES,
  CameraAccessError,
  createCameraSession,
} from "@shared/platform/camera.js";
import {
  formatDate,
  formatDateTime,
  todayInputValue,
} from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell, NameCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { CameraPreviewWindow } from "@ui/display/CameraPreviewWindow.jsx";

import { AttendancePercentageProbe } from "./AttendancePercentageProbe.jsx";
import { AttendancePresenceWindow } from "./AttendancePresenceWindow.jsx";
import { DayStatusProbe } from "./DayStatusProbe.jsx";
import { JornadaParametersWindow } from "./JornadaParametersWindow.jsx";
import { ScanCaptureWindow } from "./ScanCaptureWindow.jsx";

// Keep the optional closure workflow out of the route's initial download.
// Service callbacks are passed as props so its chunk does not import this route.
const SectionClosureWindow = lazy(() =>
  import("./SectionClosureWindow.jsx").then((module) => ({
    default: module.SectionClosureWindow,
  }))
);

const eventColumns = (names) => [
  {
    key: "student_id",
    label: "Estudiante",
    render: (row) => <NameCell id={row.student_id} index={names.students} />,
  },
  {
    key: "shift_id",
    label: "Jornada",
    render: (row) => <NameCell id={row.shift_id} index={names.shifts} />,
  },
  {
    key: "event_date",
    label: "Fecha",
    render: (row) => formatDate(row.event_date),
  },
  {
    key: "movement_type",
    label: "Movimiento",
    render: (row) => (
      <StatusChip
        label={MOVEMENT_LABEL[row.movement_type] ?? row.movement_type}
        variant={MOVEMENT_VARIANT[row.movement_type] ?? "neutral"}
      />
    ),
  },
  {
    key: "origin",
    label: "Origen",
    render: (row) => (
      <StatusChip
        label={ORIGIN_LABEL[row.origin] ?? row.origin}
        variant={ORIGIN_VARIANT[row.origin] ?? "neutral"}
      />
    ),
  },
  {
    key: "transmission",
    label: "Transmision",
    render: (row) =>
      row.transmission ? (
        (TRANSMISSION_LABEL[row.transmission] ?? row.transmission)
      ) : (
        <MutedCell>Sin dato</MutedCell>
      ),
  },
  {
    key: "captured_at",
    label: "Capturado",
    render: (row) => formatDateTime(row.captured_at),
  },
  {
    key: "is_active",
    label: "Vigente",
    render: (row) =>
      row.is_active === false ? (
        <StatusChip label="Suprimido" variant="neutral" />
      ) : (
        <StatusChip label="Vigente" variant="success" />
      ),
  },
];

const alertColumns = (names) => [
  {
    key: "alert_type",
    label: "Alerta",
    render: (row) => (
      <StatusChip
        label={ATTENDANCE_ALERT_LABEL[row.alert_type] ?? row.alert_type}
        variant={ATTENDANCE_ALERT_VARIANT[row.alert_type] ?? "warning"}
      />
    ),
  },
  {
    key: "student_id",
    label: "Estudiante",
    render: (row) => <NameCell id={row.student_id} index={names.students} />,
  },
  {
    key: "event_date",
    label: "Fecha",
    render: (row) => formatDate(row.event_date),
  },
  {
    key: "section_id",
    label: "Seccion",
    render: (row) =>
      row.section_id ? (
        <NameCell id={row.section_id} index={names.sections} />
      ) : (
        <MutedCell>Sin seccion</MutedCell>
      ),
  },
  {
    key: "created_at",
    label: "Emitida",
    render: (row) => formatDateTime(row.created_at),
  },
];

const eventFields = ({ shifts, students }) => [
  {
    name: "student_id",
    label: "Estudiante",
    type: "select",
    options: students.options,
    loading: students.loading,
    optionsError: students.error,
    emptyHint: "No hay estudiantes registrados.",
    required: true,
  },
  {
    name: "shift_id",
    label: "Jornada",
    type: "select",
    options: shifts.options,
    loading: shifts.loading,
    optionsError: shifts.error,
    emptyHint: "No hay jornadas registradas.",
    required: true,
  },
  {
    name: "event_date",
    label: "Fecha del movimiento",
    type: "date",
    required: true,
  },
  {
    name: "movement_type",
    label: "Movimiento",
    type: "select",
    options: [
      { value: "entry", label: "Entrada" },
      { value: "exit", label: "Salida" },
    ],
    required: true,
  },
  {
    name: "origin",
    label: "Origen",
    type: "select",
    options: [
      { value: "manual", label: "Manual" },
      { value: "scan", label: "Lectura" },
      { value: "declared", label: "Declarada" },
    ],
    required: true,
  },
  {
    name: "captured_at",
    label: "Momento de captura",
    type: "date",
    required: true,
    help: "El backend registra la hora de captura; la fecha del movimiento puede ser anterior.",
  },
];

/**
 * Asistencia: eventos de entrada y salida, alertas de la jornada y consulta del
 * estado del dia.
 *
 * Los eventos NO se editan ni se borran: el backend suprime duplicados marcando
 * `is_active=false` y conserva el registro. La columna "Vigente" existe para que
 * eso sea visible en vez de parecer que un movimiento desaparecio.
 */
export function AttendancePage() {
  const students = useStudentCatalog();
  const shifts = useShiftCatalog();
  const sections = useSectionCatalog();

  const names = useMemo(
    () => ({
      students: labelIndex(students.options),
      shifts: labelIndex(shifts.options),
      sections: labelIndex(sections.options),
    }),
    [students.options, shifts.options, sections.options]
  );

  const loadEvents = useCallback(
    (params) => attendanceService.listEvents(params),
    []
  );
  const loadAlerts = useCallback(
    (params) => attendanceService.listAlerts(params),
    []
  );

  // Paginacion del servidor: el registro de movimientos crece con cada dia de
  // clases, asi que traerlo completo para filtrar en memoria no escala.
  const events = usePaginatedList(loadEvents, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const alerts = usePaginatedList(loadAlerts, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [creating, setCreating] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [showParameters, setShowParameters] = useState(false);
  const [showScan, setShowScan] = useState(false);
  const [showPresence, setShowPresence] = useState(false);
  const [showSectionClosure, setShowSectionClosure] = useState(false);
  const [cameraPreflightError, setCameraPreflightError] = useState(null);

  // RNF-USA-001: el permiso de camara se verifica al entrar a la captura de
  // asistencia, no en el primer escaneo. La sesion se libera de inmediato --
  // solo importa que el navegador haya resuelto el permiso, no mantener el
  // hardware ocupado antes de que el operador abra la vista previa.
  useEffect(() => {
    let disposed = false;

    createCameraSession()
      .then((session) => {
        session.stop();
        if (!disposed) setCameraPreflightError(null);
      })
      .catch((error) => {
        if (disposed) return;
        const code =
          error instanceof CameraAccessError ? error.code : "unavailable";
        setCameraPreflightError(code);
      });

    return () => {
      disposed = true;
    };
  }, []);

  const handleCreateEvent = async (payload) => {
    await attendanceService.createEvent(payload);
    setCreating(false);
    events.refresh();
    // Un movimiento nuevo puede resolver o generar alertas del dia.
    alerts.refresh();
  };

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" flexWrap="wrap" gap={1}>
            <Button
              onClick={() => setShowPresence(true)}
              startIcon={<GroupsOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Presencia en tiempo real
            </Button>
            <Button
              onClick={() => setShowCamera(true)}
              startIcon={<PhotoCameraOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Abrir camara
            </Button>
            <Button
              onClick={() => setShowParameters(true)}
              startIcon={<TuneOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Parametros de jornada
            </Button>
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="outlined"
            >
              Registrar movimiento
            </Button>
            <Button
              onClick={() => setShowSectionClosure(true)}
              startIcon={<TaskAltOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Cerrar seccion
            </Button>
            <Button
              onClick={() => setShowScan(true)}
              startIcon={<QrCodeScannerOutlinedIcon fontSize="small" />}
              variant="contained"
            >
              Registrar por escaneo
            </Button>
          </Stack>
        }
        breadcrumb="Control de asistencia"
        subtitle="Movimientos de entrada y salida, alertas de la jornada y consulta del estado del dia de un estudiante."
        title="Asistencia"
      />

      {cameraPreflightError ? (
        <Alert
          onClose={() => setCameraPreflightError(null)}
          severity="warning"
          sx={{ mb: 2 }}
        >
          {CAMERA_ERROR_MESSAGES[cameraPreflightError] ??
            CAMERA_ERROR_MESSAGES.unavailable}
        </Alert>
      ) : null}

      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <DayStatusProbe />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <AttendancePercentageProbe />
        </Grid>
      </Grid>

      <SectionCard
        subtitle="Emitidas por el cierre de jornada"
        sx={{ mb: 2 }}
        title="Alertas de asistencia"
      >
        {alerts.error ? (
          <Alert severity="error" sx={{ m: 2 }}>
            {alerts.error}
          </Alert>
        ) : null}
        <SectionTableArea>
          <DataTable
            columns={alertColumns(names)}
            emptyMessage="Sin alertas de asistencia registradas."
            getRowKey={(row) => row.public_id}
            loading={alerts.loading}
            pagination={alerts.pagination}
            rows={alerts.items}
          />
        </SectionTableArea>
      </SectionCard>

      <SectionCard
        fillHeight
        subtitle="Registro completo, duplicados incluidos"
        title="Movimientos"
      >
        {events.error ? (
          <Alert severity="error" sx={{ m: 2 }}>
            {events.error}
          </Alert>
        ) : null}
        <SectionTableArea>
          <DataTable
            columns={eventColumns(names)}
            emptyMessage="Todavia no hay movimientos registrados."
            fillHeight
            getRowKey={(row) => row.public_id}
            loading={events.loading}
            pagination={events.pagination}
            rows={events.items}
          />
        </SectionTableArea>
      </SectionCard>

      <EntityFormWindow
        description="Un movimiento manual queda marcado con origen distinto al de lectura, para poder auditarlo despues."
        fields={eventFields({ shifts, students })}
        // Las dos fechas arrancan en hoy: un movimiento se registra el dia que
        // ocurre, y las dos se pueden corregir con el mismo campo si se esta
        // cargando algo atrasado.
        initialValues={{
          student_id: "",
          shift_id: "",
          event_date: todayInputValue(),
          movement_type: "entry",
          origin: "manual",
          captured_at: todayInputValue(),
        }}
        key={creating ? "event-create-open" : "event-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreateEvent}
        open={creating}
        submitLabel="Registrar movimiento"
        title="Nuevo movimiento de asistencia"
      />

      {showParameters ? (
        <JornadaParametersWindow onClose={() => setShowParameters(false)} />
      ) : null}

      {showCamera ? (
        <CameraPreviewWindow onClose={() => setShowCamera(false)} />
      ) : null}

      {showScan ? (
        <ScanCaptureWindow
          onClose={() => setShowScan(false)}
          onRecorded={() => {
            events.refresh();
            alerts.refresh();
          }}
        />
      ) : null}

      {showPresence ? (
        <AttendancePresenceWindow onClose={() => setShowPresence(false)} />
      ) : null}

      {showSectionClosure ? (
        <Suspense
          fallback={
            <CircularProgress
              aria-label="Cargando cierre de seccion"
              size={24}
            />
          }
        >
          <SectionClosureWindow
            previewClosure={attendanceService.previewSectionClosure}
            submitClosure={attendanceService.closeSection}
            onClosed={() => {
              events.refresh();
              alerts.refresh();
            }}
            onClose={() => setShowSectionClosure(false)}
          />
        </Suspense>
      ) : null}
    </>
  );
}
