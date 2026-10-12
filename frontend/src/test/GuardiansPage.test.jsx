import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GuardiansPage } from "@guardians/GuardiansPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  fillInstitutionalPerson,
  institutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const guardiansServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
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
      public_id: "person-31",
      first_name: "Rosa Elvira",
      last_name: "Garcia Mendez",
      email: "rosa@example.test",
      phone_number: "4512-7890",
    },
  },
  {
    id: 2,
    person: {
      public_id: "person-32",
      first_name: "Marco Tulio",
      last_name: "Ramirez Us",
      email: "marco@example.test",
      phone_number: "3398-1122",
    },
  },
];

describe("GuardiansPage", () => {
  beforeEach(() => {
    guardiansServiceMock.list.mockReset();
    guardiansServiceMock.create.mockReset();
    guardiansServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(downloadCsvMock).toHaveBeenCalledTimes(1);
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("padres-de-familia.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("renders the list once loaded", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Rosa Elvira Garcia Mendez")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("rosa@example.test")
    ).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1–2 de 2/)).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.type(screen.getByPlaceholderText("Buscar por nombre…"), "Nadie");

    expect(
      await screen.findByText("Sin resultados para la busqueda.")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    guardiansServiceMock.list.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    const panel = screen.getByRole("dialog");
    expect(
      within(panel).getByRole("heading", { name: "Rosa Elvira Garcia Mendez" })
    ).toBeInTheDocument();
    expect(within(panel).getByText("rosa@example.test")).toBeInTheDocument();
  });

  test("submits the create form against the service", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    guardiansServiceMock.create.mockResolvedValue({
      id: 3,
      person: {
        public_id: "person-33",
        first_name: "Nuevo",
        last_name: "Encargado",
        email: "",
        phone_number: "",
      },
    });
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: /Nuevo encargado/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nuevo");
    await user.type(screen.getByLabelText(/^Apellidos/), "Encargado");
    await fillInstitutionalPerson(user);
    await user.click(screen.getByRole("button", { name: /Crear encargado/ }));

    await waitFor(() =>
      expect(guardiansServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(guardiansServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          ...institutionalPerson,
          first_name: "Nuevo",
          last_name: "Encargado",
        },
      })
    );
    expect(await screen.findByText("Nuevo Encargado")).toBeInTheDocument();
  });

  test("edits a guardian via the detail panel", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    guardiansServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        public_id: "person-31",
        first_name: "Rosa Elvira",
        last_name: "Garcia Lopez",
        email: "rosa@example.test",
        phone_number: "4512-7890",
      },
    });
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Garcia Mendez");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Garcia Lopez");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(guardiansServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(guardiansServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          id: "person-31",
          first_name: "Rosa Elvira",
          last_name: "Garcia Lopez",
          email: "rosa@example.test",
          phone_number: "4512-7890",
        },
      })
    );
    expect(
      await screen.findByRole("heading", { name: "Rosa Elvira Garcia Lopez" })
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: /Nuevo encargado/ }));
    await user.click(screen.getByRole("button", { name: /Crear encargado/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(guardiansServiceMock.create).not.toHaveBeenCalled();
  });
});
