import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AlumnosPage } from "@students/AlumnosPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  fillInstitutionalPerson,
  institutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const studentsServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  // Ver el doble homonimo en DocentesPage.test.jsx: el alta pide el codigo
  // sugerido al abrir, y sin esto la prueba corre por el camino de error.
  nextCode: vi.fn(),
  listHealthNotes: vi.fn(),
  createHealthNote: vi.fn(),
  listObservations: vi.fn(),
  createObservation: vi.fn(),
  listEmergencyContacts: vi.fn(),
  createEmergencyContact: vi.fn(),
  listGuardianRelations: vi.fn(),
  createGuardianRelation: vi.fn(),
}));

const guardiansServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
}));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("@shared/utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    person: {
      ...visibleInstitutionalPerson,
      public_id: "person-11",
      first_name: "Maria Jose",
      last_name: "Lopez Garcia",
      email: "maria@example.test",
      phone_number: "555-0101",
    },
    student_code: "EST-2026-014",
    status: "active",
    photo: "http://localhost/media/student_photos/maria.png",
  },
  {
    id: 2,
    person: {
      public_id: "person-12",
      first_name: "Carlos Enrique",
      last_name: "Ramirez Perez",
      email: "carlos@example.test",
      phone_number: "555-0102",
    },
    student_code: "EST-2026-015",
    status: "active",
    photo: "",
  },
];

describe("AlumnosPage", () => {
  beforeEach(() => {
    studentsServiceMock.list.mockReset();
    studentsServiceMock.create.mockReset();
    studentsServiceMock.update.mockReset();
    studentsServiceMock.listHealthNotes.mockReset();
    studentsServiceMock.createHealthNote.mockReset();
    studentsServiceMock.listHealthNotes.mockResolvedValue([]);
    studentsServiceMock.listObservations.mockReset();
    studentsServiceMock.createObservation.mockReset();
    studentsServiceMock.listObservations.mockResolvedValue([]);
    studentsServiceMock.listEmergencyContacts.mockReset();
    studentsServiceMock.createEmergencyContact.mockReset();
    studentsServiceMock.listEmergencyContacts.mockResolvedValue([]);
    studentsServiceMock.listGuardianRelations.mockReset();
    studentsServiceMock.createGuardianRelation.mockReset();
    studentsServiceMock.listGuardianRelations.mockResolvedValue([]);
    guardiansServiceMock.list.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(downloadCsvMock).toHaveBeenCalledTimes(1);
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("alumnos.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("renders the list once loaded", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    renderWithRouter(<AlumnosPage />);

    expect(
      await screen.findByText("Maria Jose Lopez Garcia")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("EST-2026-014")
    ).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1–2 de 2/)).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.type(screen.getByPlaceholderText("Buscar por nombre…"), "Nadie");

    expect(
      await screen.findByText("Sin resultados para la busqueda.")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    studentsServiceMock.list.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<AlumnosPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.getByRole("heading", { name: "Maria Jose Lopez Garcia" })
    ).toBeInTheDocument();
    expect(screen.getByText("maria@example.test")).toBeInTheDocument();
  });

  test("opens and closes the photo lightbox from the detail panel", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.queryByRole("dialog", { name: "Foto de Maria Jose Lopez Garcia" })
    ).not.toBeInTheDocument();

    const detailWindow = screen.getByRole("dialog", {
      name: "Maria Jose Lopez Garcia",
    });
    await user.click(
      within(detailWindow).getByAltText("Foto de Maria Jose Lopez Garcia")
    );

    const lightbox = screen.getByRole("dialog", {
      name: "Foto de Maria Jose Lopez Garcia",
    });
    const downloadLink = within(lightbox).getByRole("link", {
      name: "Descargar",
    });
    expect(downloadLink).toHaveAttribute(
      "href",
      "http://localhost/media/student_photos/maria.png"
    );
    expect(downloadLink).toHaveAttribute("download", "maria.png");

    await user.click(
      within(lightbox).getByRole("button", { name: "Cerrar imagen" })
    );
    // El dialogo se desmonta al terminar su animacion de salida, no en el clic.
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", {
          name: "Foto de Maria Jose Lopez Garcia",
        })
      ).not.toBeInTheDocument()
    );
  });

  test("submits the create form against the mock service", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    studentsServiceMock.nextCode.mockResolvedValue("EST-2026-0101");
    studentsServiceMock.create.mockResolvedValue({
      id: 3,
      person: {
        public_id: "person-13",
        first_name: "Nueva",
        last_name: "Alumna",
        email: "",
        phone_number: "",
      },
      student_code: "EST-2026-099",
      status: "pre_enrolled",
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nueva");
    await user.type(screen.getByLabelText(/^Apellidos/), "Alumna");
    await fillInstitutionalPerson(user);
    await user.type(screen.getByLabelText(/^Correo/), "nueva@example.test");
    const codeField = screen.getByLabelText(/^Codigo de estudiante/);
    // Llega prellenado con la sugerencia del backend, y se puede sobreescribir:
    // un traslado trae su codigo ya impreso en los papeles.
    expect(codeField).toHaveValue("EST-2026-0101");
    await user.clear(codeField);
    await user.type(codeField, "EST-2026-099");
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    await waitFor(() =>
      expect(studentsServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          ...institutionalPerson,
          first_name: "Nueva",
          last_name: "Alumna",
          email: "nueva@example.test",
          phone_number: "555-0199",
        },
        student_code: "EST-2026-099",
        status: "pre_enrolled",
      })
    );
    expect(await screen.findByText("Nueva Alumna")).toBeInTheDocument();
    // Ver el presupuesto homonimo en DocentesPage.test.jsx.
  }, 15000);

  test("previews a newly selected photo in the create form", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    expect(screen.queryByAltText("Vista previa")).not.toBeInTheDocument();

    const file = new File(["fake-image-bytes"], "avatar.png", {
      type: "image/png",
    });
    await user.upload(screen.getByLabelText(/^Foto/), file);

    expect(await screen.findByAltText("Vista previa")).toHaveAttribute(
      "src",
      "blob:mock-url"
    );
  });

  test("edits a student via the detail panel", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    studentsServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        public_id: "person-11",
        first_name: "Maria Jose",
        last_name: "Lopez Mendez",
        email: "maria@example.test",
        phone_number: "555-0101",
      },
      student_code: "EST-2026-014",
      status: "active",
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Lopez Garcia");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Lopez Mendez");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(studentsServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          id: "person-11",
          first_name: "Maria Jose",
          last_name: "Lopez Mendez",
          email: "maria@example.test",
          phone_number: "555-0101",
        },
        student_code: "EST-2026-014",
        status: "active",
      })
    );
    expect(
      await screen.findByRole("heading", { name: "Maria Jose Lopez Mendez" })
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(studentsServiceMock.create).not.toHaveBeenCalled();
  });

  test("opens sensitive health section and creates a note", async () => {
    studentsServiceMock.list.mockResolvedValue([
      { ...SAMPLE[0], public_id: "11111111-1111-1111-1111-111111111111" },
    ]);
    studentsServiceMock.createHealthNote.mockResolvedValue({
      public_id: "22222222-2222-2222-2222-222222222222",
      author: "directora",
      content: "Alergia de prueba",
      recorded_on: "2026-08-17",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Ver detalle/ }));
    await user.click(screen.getByRole("button", { name: "Salud" }));

    expect(await screen.findByText("Sin notas de salud")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Nueva nota" }));
    await user.type(
      screen.getByLabelText(/^Información de salud/),
      "Alergia de prueba"
    );
    await user.click(screen.getByRole("button", { name: "Registrar nota" }));

    await waitFor(() =>
      expect(studentsServiceMock.createHealthNote).toHaveBeenCalledWith(
        "11111111-1111-1111-1111-111111111111",
        { content: "Alergia de prueba" }
      )
    );
    expect(await screen.findByText("Alergia de prueba")).toBeInTheDocument();
  });

  test("links a guardian from the student detail", async () => {
    const guardian = {
      id: 21,
      person: {
        public_id: "person-31",
        first_name: "Rosa",
        last_name: "Garcia",
        email: "rosa@example.test",
        phone_number: "555-0103",
      },
    };
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    guardiansServiceMock.list.mockResolvedValue([guardian]);
    studentsServiceMock.createGuardianRelation.mockResolvedValue({
      id: 41,
      student: 1,
      guardian: guardian.id,
      guardian_detail: guardian,
      relationship_label: "Madre",
      is_primary: true,
      ends_at: null,
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(
      screen.getByRole("button", { name: "Vincular encargado" })
    );

    await waitFor(() =>
      expect(guardiansServiceMock.list).toHaveBeenCalledTimes(1)
    );
    await user.click(
      await screen.findByRole("combobox", { name: /^Encargado/ })
    );
    await user.click(
      screen.getByRole("option", { name: "Rosa Garcia · rosa@example.test" })
    );
    await user.type(
      screen.getByLabelText(/^Parentesco o responsabilidad/),
      "Madre"
    );
    await user.click(
      screen.getAllByRole("button", { name: "Vincular encargado" }).at(-1)
    );

    await waitFor(() =>
      expect(studentsServiceMock.createGuardianRelation).toHaveBeenCalledWith({
        student: 1,
        guardian: 21,
        relationship_label: "Madre",
      })
    );
    expect(await screen.findByText("Rosa Garcia")).toBeInTheDocument();
    expect(screen.getByText(/Madre.*Principal/)).toBeInTheDocument();
  });

  test("opens sensitive observations and creates one", async () => {
    studentsServiceMock.list.mockResolvedValue([
      { ...SAMPLE[0], public_id: "11111111-1111-1111-1111-111111111111" },
    ]);
    studentsServiceMock.createObservation.mockResolvedValue({
      public_id: "22222222-2222-2222-2222-222222222222",
      author: "directora",
      description: "Seguimiento pedagogico",
      observed_on: "2026-08-17",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Ver detalle/ }));
    await user.click(screen.getByRole("button", { name: "Observaciones" }));
    expect(await screen.findByText("Sin observaciones")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Nueva observación" }));
    await user.type(
      screen.getByLabelText(/^Descripción/),
      "Seguimiento pedagogico"
    );
    await user.click(
      screen.getByRole("button", { name: "Registrar observación" })
    );

    await waitFor(() =>
      expect(studentsServiceMock.createObservation).toHaveBeenCalledWith(
        "11111111-1111-1111-1111-111111111111",
        { description: "Seguimiento pedagogico" }
      )
    );
    expect(
      await screen.findByText("Seguimiento pedagogico")
    ).toBeInTheDocument();
  });

  test("lists and creates an emergency contact", async () => {
    studentsServiceMock.list.mockResolvedValue([
      { ...SAMPLE[0], public_id: "11111111-1111-1111-1111-111111111111" },
    ]);
    studentsServiceMock.createEmergencyContact.mockResolvedValue({
      public_id: "33333333-3333-3333-3333-333333333333",
      name: "Ana López",
      phone_number: "555-0104",
      relationship_label: "Tía",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Ver detalle/ }));
    await user.click(
      screen.getByRole("button", { name: "Contactos de emergencia" })
    );
    expect(
      await screen.findByText("Sin contactos de emergencia")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Nuevo contacto" }));
    await user.type(screen.getByLabelText(/^Nombre/), "Ana López");
    await user.type(screen.getByLabelText(/^Teléfono/), "555-0104");
    await user.type(screen.getByLabelText(/^Relación/), "Tía");
    await user.click(
      screen.getByRole("button", { name: "Registrar contacto" })
    );

    await waitFor(() =>
      expect(studentsServiceMock.createEmergencyContact).toHaveBeenCalledWith(
        "11111111-1111-1111-1111-111111111111",
        {
          name: "Ana López",
          phone_number: "555-0104",
          relationship_label: "Tía",
        }
      )
    );
    expect(await screen.findByText("Ana López · Tía")).toBeInTheDocument();
  });

  test("opens sensitive observations and creates one", async () => {
    studentsServiceMock.list.mockResolvedValue([
      { ...SAMPLE[0], public_id: "11111111-1111-1111-1111-111111111111" },
    ]);
    studentsServiceMock.createObservation.mockResolvedValue({
      public_id: "22222222-2222-2222-2222-222222222222",
      author: "directora",
      description: "Seguimiento pedagogico",
      observed_on: "2026-08-17",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Ver detalle/ }));
    await user.click(screen.getByRole("button", { name: "Observaciones" }));
    expect(await screen.findByText("Sin observaciones")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Nueva observación" }));
    await user.type(
      screen.getByLabelText(/^Descripción/),
      "Seguimiento pedagogico"
    );
    await user.click(
      screen.getByRole("button", { name: "Registrar observación" })
    );

    await waitFor(() =>
      expect(studentsServiceMock.createObservation).toHaveBeenCalledWith(
        "11111111-1111-1111-1111-111111111111",
        { description: "Seguimiento pedagogico" }
      )
    );
    expect(
      await screen.findByText("Seguimiento pedagogico")
    ).toBeInTheDocument();
  });
});
