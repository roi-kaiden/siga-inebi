import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { FinalGradeWindow } from "@evaluation/FinalGradeWindow.jsx";
import { evaluationService } from "@evaluation/evaluationService.js";
import { selectOption } from "./helpers/selectOption.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

vi.mock("@evaluation/evaluationService.js", () => ({
  evaluationService: { getFinalSubjectGrade: vi.fn() },
}));
vi.mock("@shared/catalogs/academicCatalogs.js", () => ({
  useEnrolmentCatalog: () => ({
    options: [{ value: "enrolment-1", label: "Estudiante de prueba" }],
  }),
  useSubjectCatalog: () => ({
    options: [{ value: "subject-1", label: "Matematica" }],
  }),
}));

describe("FinalGradeWindow — INC-008", () => {
  it.each([
    [59.5, 60, 2, "60"],
    [59.4, 59, 2, "59"],
    [0, 0, 2, "0"],
    [null, null, 0, "Sin calificar"],
  ])(
    "muestra final_grade para promedio %s",
    async (average, finalGrade, graded, expected) => {
      evaluationService.getFinalSubjectGrade.mockResolvedValue({
        average,
        final_grade: finalGrade,
        graded_units: graded,
        total_units: 2,
        pending_units: 2 - graded,
      });
      const user = userEvent.setup();
      renderWithRouter(
        <FinalGradeWindow cycleId="cycle-1" onClose={vi.fn()} />
      );
      await selectOption(user, /Estudiante/, "Estudiante de prueba");
      await selectOption(user, /Subarea/, "Matematica");
      await user.click(
        screen.getByRole("button", { name: "Consultar", exact: true })
      );
      expect(
        await screen.findByRole("heading", { level: 4 })
      ).toHaveTextContent(new RegExp(`^${expected}$`));
      expect(evaluationService.getFinalSubjectGrade).toHaveBeenCalledWith(
        "cycle-1",
        "enrolment-1",
        "subject-1"
      );
    }
  );

  it("permite consultar el resultado usando solo el teclado", async () => {
    evaluationService.getFinalSubjectGrade.mockResolvedValue({
      average: 59.5,
      final_grade: 60,
      graded_units: 2,
      total_units: 2,
      pending_units: 0,
    });
    const user = userEvent.setup();
    renderWithRouter(<FinalGradeWindow cycleId="cycle-1" onClose={vi.fn()} />);

    const dialog = screen.getByRole("dialog", { name: "Consultar resultado" });
    const student = screen.getByRole("combobox", { name: "Estudiante" });
    const subject = screen.getByRole("combobox", { name: "Subarea" });
    const query = screen.getByRole("button", {
      name: "Consultar",
      exact: true,
    });
    expect(dialog).toContainElement(student);
    expect(query).toBeDisabled();

    for (
      let step = 0;
      step < 5 && document.activeElement !== student;
      step += 1
    ) {
      await user.tab();
    }
    expect(student).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    await screen.findByRole("listbox");
    await user.keyboard("{End}{Enter}");
    expect(student).toHaveTextContent("Estudiante de prueba");
    await user.tab();
    expect(subject).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    await screen.findByRole("listbox");
    await user.keyboard("{End}{Enter}");
    expect(subject).toHaveTextContent("Matematica");
    await user.tab();
    expect(query).toHaveFocus();
    expect(query).toBeEnabled();
    await user.keyboard("{Enter}");

    expect(await screen.findByRole("heading", { level: 4 })).toHaveTextContent(
      /^60$/
    );
    expect(evaluationService.getFinalSubjectGrade).toHaveBeenCalledWith(
      "cycle-1",
      "enrolment-1",
      "subject-1"
    );
  });
});
