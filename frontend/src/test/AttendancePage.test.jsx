import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { CAMERA_ERROR, CameraAccessError } from "@shared/platform/camera.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

const attendanceServiceMock = vi.hoisted(() => ({
  listJornadaParameters: vi.fn(),
  createJornadaParameters: vi.fn(),
  listEvents: vi.fn(),
  createEvent: vi.fn(),
  eventResolution: vi.fn(),
  dayStatus: vi.fn(),
  closeJornada: vi.fn(),
  previewSectionClosure: vi.fn(),
  closeSection: vi.fn(),
  listAlerts: vi.fn(),
  listControlPoints: vi.fn(),
  recordScan: vi.fn(),
  listPresence: vi.fn(),
  attendancePercentage: vi.fn(),
}));

const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));

const createCameraSessionMock = vi.hoisted(() => vi.fn());

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});

// RNF-USA-001: el chequeo preventivo de camara corre al montar la pagina;
// sin doble se dispararia una peticion real de getUserMedia en jsdom.
vi.mock("@shared/platform/camera.js", async () => {
  const actual = await vi.importActual("@shared/platform/camera.js");
  return { ...actual, createCameraSession: createCameraSessionMock };
});

// Los selectores de jornada, grado, seccion y estudiante leen los catalogos, y
// sin doble irian a la red: en jsdom eso queda como un catalogo vacio y ninguna
// opcion que elegir.
vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const paged = (results) => ({ count: results.length, results });

const CAMPUS = { public_id: "campus-1", name: "Sede Central" };

const SHIFT = {
  public_id: "shift-1",
  name: "Matutina",
  code: "MAT",
  campus: CAMPUS,
};

const STUDENT = {
  public_id: "student-1",
  student_code: "EST-1",
  person: { first_name: "Luis", last_name: "Perez" },
};

const SECTION = {
  public_id: "section-1",
  name: "A",
  capacity: 30,
  academic_cycle_id: "cycle-1",
  grade: { public_id: "grade-1", name: "Primero Basico" },
  shift: { public_id: SHIFT.public_id, name: "Matutina" },
};

const CONTROL_POINT = {
  public_id: "cp-1",
  name: "Porton principal",
  code: "PP-1",
  campus_id: "campus-1",
  is_active: true,
};

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  attendanceServiceMock.listEvents.mockResolvedValue(paged([]));
  attendanceServiceMock.listAlerts.mockResolvedValue(paged([]));
  attendanceServiceMock.listControlPoints.mockResolvedValue(
    paged([CONTROL_POINT])
  );

  resetAcademicsServiceMock();
  academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
  academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
  academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));

  createCameraSessionMock
    .mockReset()
    .mockResolvedValue({ stream: null, stop: vi.fn() });
});

async function openScanWindow(user) {
  await user.click(
    screen.getByRole("button", { name: "Registrar por escaneo" })
  );
  return screen.findByRole("dialog", { name: "Registrar por escaneo" });
}

describe("AttendancePage — captura por escaneo", () => {
  test("registra un movimiento y muestra el resultado", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue([
      {
        client_event_id: "any",
        outcome: "created",
        event: { origin: "scan", movement_type: "entry" },
        duplicate_of: null,
        reason: "",
      },
    ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-001"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Registrar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(1)
    );
    const payload = attendanceServiceMock.recordScan.mock.calls[0][0];
    expect(payload.items[0]).toEqual(
      expect.objectContaining({
        student_code: "EST-001",
        control_point_id: "cp-1",
        shift_id: "shift-1",
        movement_type: "entry",
      })
    );
    expect(payload.items[0].client_event_id).toEqual(expect.any(String));

    expect(await within(dialog).findByText("Registrado")).toBeInTheDocument();
  }, 10000);

  test("informa la hora del movimiento duplicado sin crear uno nuevo", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue([
      {
        client_event_id: "any",
        outcome: "duplicate_suppressed",
        event: null,
        duplicate_of: {
          movement_type: "entry",
          captured_at: "2026-08-19T13:00:00Z",
        },
        reason: "",
      },
    ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-002"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Registrar" }));

    expect(
      await within(dialog).findByText("Ya estaba registrado")
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/ya registrado a las/)).toBeInTheDocument();
  }, 10000);

  test("reintenta con el mismo client_event_id tras un fallo de red", async () => {
    attendanceServiceMock.recordScan
      .mockRejectedValueOnce(new Error("La red fallo."))
      .mockResolvedValueOnce([
        {
          client_event_id: "any",
          outcome: "created",
          event: {},
          duplicate_of: null,
          reason: "",
        },
      ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-003"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);

    const submitButton = within(dialog).getByRole("button", {
      name: "Registrar",
    });
    await user.click(submitButton);
    expect(
      await within(dialog).findByText("La red fallo.")
    ).toBeInTheDocument();

    await user.click(submitButton);
    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(2)
    );

    const firstId =
      attendanceServiceMock.recordScan.mock.calls[0][0].items[0]
        .client_event_id;
    const secondId =
      attendanceServiceMock.recordScan.mock.calls[1][0].items[0]
        .client_event_id;
    expect(secondId).toBe(firstId);
  }, 10000);
});

describe("AttendancePage — cierre declarado por cobertura", () => {
  test("abre, cierra y reabre el cierre diferido sin ejecutar operaciones", async () => {
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    expect(
      screen.queryByRole("dialog", { name: "Cierre declarado por seccion" })
    ).not.toBeInTheDocument();

    for (let attempt = 0; attempt < 2; attempt += 1) {
      await user.click(screen.getByRole("button", { name: "Cerrar seccion" }));
      const dialog = await screen.findByRole("dialog", {
        name: "Cierre declarado por seccion",
      });
      await user.click(
        within(dialog).getAllByRole("button", { name: "Cerrar" })[attempt]
      );
      await waitFor(() => expect(dialog).not.toBeInTheDocument());
    }

    expect(attendanceServiceMock.previewSectionClosure).not.toHaveBeenCalled();
    expect(attendanceServiceMock.closeSection).not.toHaveBeenCalled();
  }, 10000);

  test("muestra la confirmacion visible antes del cierre por cobertura", async () => {
    attendanceServiceMock.previewSectionClosure.mockResolvedValue({
      section_id: "section-1",
      grade_name: "Primero Basico",
      event_date: "2026-09-05",
      included: [{ student_id: "student-1" }],
      omitted: [],
      is_covering: false,
      confirmation_required: false,
    });
    attendanceServiceMock.closeSection
      .mockResolvedValueOnce({
        section_id: "section-1",
        grade_name: "Primero Basico",
        event_date: "2026-09-05",
        included: [{ student_id: "student-1" }],
        omitted: [],
        is_covering: true,
        confirmation_required: true,
      })
      .mockResolvedValueOnce({
        section_id: "section-1",
        grade_name: "Primero Basico",
        event_date: "2026-09-05",
        included: [{ student_id: "student-1" }],
        omitted: [],
        is_covering: true,
        confirmation_required: false,
      });
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    await user.click(screen.getByRole("button", { name: "Cerrar seccion" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Cierre declarado por seccion",
    });
    await selectOption(user, /^Seccion/, /Primero Basico A/, dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "Previsualizar cierre" })
    );
    expect(await within(dialog).findByText("1 por cerrar")).toBeInTheDocument();

    await user.click(
      within(dialog).getByRole("button", { name: "Declarar cierre" })
    );
    const confirmation = await screen.findByRole("dialog", {
      name: "Confirmar cierre por cobertura",
    });
    expect(
      within(confirmation).getByText(/Actuara como docente de cobertura/)
    ).toBeInTheDocument();

    await user.click(
      within(confirmation).getByRole("button", { name: "Confirmar cierre" })
    );
    await waitFor(() =>
      expect(attendanceServiceMock.closeSection).toHaveBeenLastCalledWith({
        section_id: "section-1",
        event_date: expect.any(String),
        confirmed: true,
      })
    );
    expect(
      await within(dialog).findByText(
        "El cierre se registro y quedo en auditoria."
      )
    ).toBeInTheDocument();
  }, 10000);
});

describe("AttendancePage — presencia en tiempo real", () => {
  test("no consulta hasta que se ingresa la jornada", async () => {
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });

    expect(
      within(dialog).getByText(
        "Elija la jornada para consultar quien esta presente."
      )
    ).toBeInTheDocument();
    expect(attendanceServiceMock.listPresence).not.toHaveBeenCalled();
  }, 10000);

  test("lista a los estudiantes presentes tras buscar", async () => {
    attendanceServiceMock.listPresence.mockResolvedValue(
      paged([
        {
          student_id: "student-1",
          section_id: "section-1",
          entry_event: { captured_at: "2026-08-19T13:00:00Z" },
        },
      ])
    );
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Buscar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.listPresence).toHaveBeenCalledWith(
        expect.objectContaining({ shift_id: "shift-1" })
      )
    );
    // Nombres, no UUIDs: la tabla mostraba "student-1" y "section-1".
    expect(
      await within(dialog).findByText("Luis Perez · EST-1")
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Primero Basico A")).toBeInTheDocument();
  }, 10000);
});

describe("AttendancePage — porcentaje de asistencia", () => {
  test("muestra el porcentaje consultado", async () => {
    attendanceServiceMock.attendancePercentage.mockResolvedValue({
      elapsed_school_days: 10,
      present_days: 8,
      late_days: 1,
      percentage: 90,
    });
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    const card = screen
      .getByRole("heading", { name: "Porcentaje de asistencia" })
      .closest("section");
    const scoped = within(card);

    await user.click(scoped.getByLabelText(/^Estudiante/));
    await user.click(
      await screen.findByRole("option", { name: "Luis Perez · EST-1" })
    );
    await user.click(scoped.getByLabelText(/^Jornada/));
    await user.click(
      await screen.findByRole("option", { name: "Matutina · Sede Central" })
    );
    await user.click(scoped.getByRole("button", { name: /Consultar/ }));

    expect(await scoped.findByText("90%")).toBeInTheDocument();
    expect(
      scoped.getByText("9 de 10 dias lectivos transcurridos")
    ).toBeInTheDocument();
  }, 10000);
});

describe("AttendancePage — verificacion preventiva de camara (RNF-USA-001)", () => {
  test("camino feliz: el permiso se verifica al entrar y no muestra aviso", async () => {
    const stop = vi.fn();
    createCameraSessionMock.mockResolvedValue({ stream: null, stop });

    renderWithRouter(<AttendancePage />);

    await waitFor(() => expect(createCameraSessionMock).toHaveBeenCalled());
    await waitFor(() => expect(stop).toHaveBeenCalled());
    expect(
      screen.queryByText(/No se pudo acceder a la camara/)
    ).not.toBeInTheDocument();
  });

  test("rechazo por autorizacion: informa sin bloquear el resto de la pagina", async () => {
    createCameraSessionMock.mockRejectedValue(
      new CameraAccessError(CAMERA_ERROR.permissionDenied)
    );
    const user = userEvent.setup();

    renderWithRouter(<AttendancePage />);

    const alert = await screen.findByText(
      "No se pudo acceder a la camara. Habilita el permiso en el navegador y vuelve a intentarlo."
    );
    expect(alert).toBeInTheDocument();

    // El aviso no bloquea el resto de la pagina: el operador sigue pudiendo
    // registrar un movimiento con normalidad.
    await openScanWindow(user);
  });
});

describe("AttendancePage — sin persistencia local de datos de menores (RNF-PRI-003)", () => {
  // Lo unico que la aplicacion puede dejar en el navegador es la preferencia
  // de tema de MUI; ningun dato del estudiante.
  const ALLOWED_KEYS = ["mui-mode"];

  function storedEntries(storage) {
    return Object.keys(storage).map((key) => [key, storage.getItem(key)]);
  }

  test("escanear y consultar presencia no deja datos del estudiante en el dispositivo", async () => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    const openDatabase = vi.fn();
    vi.stubGlobal("indexedDB", { open: openDatabase });
    attendanceServiceMock.recordScan.mockResolvedValue([
      {
        client_event_id: "any",
        outcome: "created",
        event: { origin: "scan", movement_type: "entry" },
        duplicate_of: null,
        reason: "",
      },
    ]);
    attendanceServiceMock.listPresence.mockResolvedValue(
      paged([
        {
          student_id: "student-1",
          section_id: "section-1",
          entry_event: { captured_at: "2026-08-19T13:00:00Z" },
        },
      ])
    );
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    const scanDialog = await openScanWindow(user);
    await user.type(
      within(scanDialog).getByLabelText(/^Codigo de estudiante/),
      "EST-1"
    );
    await selectOption(
      user,
      /^Punto de control/,
      /Porton principal/,
      scanDialog
    );
    await selectOption(user, /^Jornada/, /Matutina/, scanDialog);
    await user.click(
      within(scanDialog).getByRole("button", { name: "Registrar" })
    );
    expect(
      await within(scanDialog).findByText("Registrado")
    ).toBeInTheDocument();
    await user.click(
      within(scanDialog).getAllByRole("button", { name: "Cerrar" })[0]
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Registrar por escaneo" })
      ).not.toBeInTheDocument()
    );

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const presenceDialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });
    await selectOption(user, /^Jornada/, /Matutina/, presenceDialog);
    await user.click(
      within(presenceDialog).getByRole("button", { name: "Buscar" })
    );
    expect(
      await within(presenceDialog).findByText("Luis Perez · EST-1")
    ).toBeInTheDocument();

    for (const storage of [window.localStorage, window.sessionStorage]) {
      for (const [key, value] of storedEntries(storage)) {
        expect(ALLOWED_KEYS).toContain(key);
        expect(value).not.toMatch(/EST-1|Luis|Perez|student-1/);
      }
    }
    expect(openDatabase).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  }, 15000);
});
