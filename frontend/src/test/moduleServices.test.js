import { beforeEach, describe, expect, test, vi } from "vitest";

import { apiClient } from "@shared/api/apiClient.js";
import { attendanceService } from "@attendance/attendanceService.js";
import { cyclesService } from "@cycles/cyclesService.js";
import { documentsService } from "@documents/documentsService.js";
import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { reportingService } from "@reporting/reportingService.js";
import { studentsService } from "@students/studentsService.js";
import { teachersService } from "@teachers/teachersService.js";
import { guardiansService } from "@guardians/guardiansService.js";

const CYCLE = "11111111-1111-1111-1111-111111111111";
const UNIT = "22222222-2222-2222-2222-222222222222";
const ENROLMENT = "33333333-3333-3333-3333-333333333333";
const TEMPLATE = "44444444-4444-4444-4444-444444444444";
const ALERT = "55555555-5555-5555-5555-555555555555";
const STUDENT = "66666666-6666-6666-6666-666666666666";
const SHIFT = "77777777-7777-7777-7777-777777777777";
const PERSON = "88888888-8888-8888-8888-888888888888";

/**
 * Contratos HTTP de los modulos cuyo backend ya existia y su UI se agrego
 * despues. Verifican la ruta y el armado del query string, que es justo lo que
 * se rompe en silencio: un endpoint mal escrito responde 404 y la pantalla
 * queda vacia sin decir por que.
 */
describe("servicios de los modulos", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "get").mockResolvedValue({ count: 0, results: [] });
    vi.spyOn(apiClient, "post").mockResolvedValue({});
    vi.spyOn(apiClient, "patch").mockResolvedValue({});
    vi.spyOn(apiClient, "del").mockResolvedValue(null);
  });

  describe("edición de personas vinculadas", () => {
    test("alumno, docente y encargado actualizan a Persona por public_id", async () => {
      await studentsService.update(1, {
        person: { public_id: PERSON, first_name: "Ana" },
      });
      expect(apiClient.patch).toHaveBeenCalledWith(`/people/${PERSON}/`, {
        first_name: "Ana",
      });

      await teachersService.update(2, {
        person: { public_id: PERSON, phone_number: "5550101" },
      });
      expect(apiClient.patch).toHaveBeenCalledWith(`/people/${PERSON}/`, {
        phone_number: "5550101",
      });

      await guardiansService.update(3, {
        person: { public_id: PERSON, email: "ana@example.test" },
      });
      expect(apiClient.patch).toHaveBeenCalledWith(`/people/${PERSON}/`, {
        email: "ana@example.test",
      });
    });
  });

  describe("cyclesService", () => {
    test("lista, crea y consulta el detalle historico", async () => {
      await cyclesService.list({ page: 2 });
      expect(apiClient.get).toHaveBeenCalledWith("/academics/cycles/?page=2");

      await cyclesService.get(CYCLE);
      expect(apiClient.get).toHaveBeenCalledWith(`/academics/cycles/${CYCLE}/`);

      await cyclesService.create({ year: 2027, name: "Ciclo 2027" });
      expect(apiClient.post).toHaveBeenCalledWith("/academics/cycles/", {
        year: 2027,
        name: "Ciclo 2027",
      });
    });

    test("activar y clonar son POST a sub-rutas del ciclo", async () => {
      await cyclesService.activate(CYCLE);
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/activate/`,
        {}
      );

      await cyclesService.clone(CYCLE, { year: 2028, name: "Ciclo 2028" });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/clone/`,
        { year: 2028, name: "Ciclo 2028" }
      );
    });
  });

  describe("enrolmentsService", () => {
    test("las matriculas vigentes se pueden filtrar por estudiante", async () => {
      await enrolmentsService.listActive({ page: 1, student_id: STUDENT });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/enrolments/active/?page=1&student_id=${STUDENT}`
      );
    });

    test("el historial viaja siempre con el estudiante, que el backend exige", async () => {
      await enrolmentsService.listHistory({ page: 1, student_id: STUDENT });
      await enrolmentsService.listMovements({ page: 1, student_id: STUDENT });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/enrolments/history/?page=1&student_id=${STUDENT}`
      );
      expect(apiClient.get).toHaveBeenCalledWith(
        `/enrolments/movements/?page=1&student_id=${STUDENT}`
      );
    });

    test("matricular y reinscribir son endpoints distintos", async () => {
      const payload = { student_id: STUDENT, academic_cycle_id: CYCLE };

      await enrolmentsService.matriculate(payload);
      expect(apiClient.post).toHaveBeenCalledWith(
        "/enrolments/matriculations/",
        payload
      );

      await enrolmentsService.reenrol(payload);
      expect(apiClient.post).toHaveBeenCalledWith(
        "/enrolments/re-enrolments/",
        payload
      );

      await enrolmentsService.create(payload);
      expect(apiClient.post).toHaveBeenCalledWith("/enrolments/", payload);
    });

    test("los requisitos documentales cuelgan de la matricula", async () => {
      await enrolmentsService.listDocuments(ENROLMENT, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/enrolments/${ENROLMENT}/documents/?page=1`
      );

      await enrolmentsService.addDocument(ENROLMENT, { code: "DPI" });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/enrolments/${ENROLMENT}/documents/`,
        { code: "DPI" }
      );
    });
  });

  describe("documentsService", () => {
    test("catalogo de plantillas y su historial de versiones", async () => {
      await documentsService.listTemplates({ include_inactive: true });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/documents/templates/?include_inactive=true"
      );

      await documentsService.listTemplateVersions(TEMPLATE, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/documents/templates/${TEMPLATE}/versions/?page=1`
      );

      await documentsService.getTemplate(TEMPLATE);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/documents/templates/${TEMPLATE}/`
      );
    });

    test("editar es PATCH y la baja es logica", async () => {
      await documentsService.createTemplate({ name: "Constancia" });
      expect(apiClient.post).toHaveBeenCalledWith("/documents/templates/", {
        name: "Constancia",
      });

      await documentsService.updateTemplate(TEMPLATE, { name: "Otra" });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/documents/templates/${TEMPLATE}/`,
        { name: "Otra" }
      );

      await documentsService.deactivateTemplate(TEMPLATE);
      expect(apiClient.del).toHaveBeenCalledWith(
        `/documents/templates/${TEMPLATE}/`
      );
    });

    test("las etiquetas sensibles no viajan si no se piden", async () => {
      await documentsService.listFieldTags({ include_sensitive: false });
      expect(apiClient.get).toHaveBeenCalledWith("/documents/field-tags/");

      await documentsService.listFieldTags({ include_sensitive: true });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/documents/field-tags/?include_sensitive=true"
      );
    });

    test("la elegibilidad de emision se consulta por matricula", async () => {
      await documentsService.issuanceEligibility(ENROLMENT);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/documents/official-issuance/eligibility/?enrolment_id=${ENROLMENT}`
      );
    });

    test("vista previa y adjuntos usan rutas separadas sin emitir documentos", async () => {
      const payload = { "student.full_name": "Estudiante de ejemplo" };
      const upload = new FormData();

      await documentsService.previewTemplate(TEMPLATE, payload);
      expect(apiClient.post).toHaveBeenCalledWith(
        `/documents/templates/${TEMPLATE}/preview/`,
        { payload }
      );

      await documentsService.listEnrolmentRecords(ENROLMENT, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/documents/enrolments/${ENROLMENT}/records/?page=1`
      );

      await documentsService.uploadRecord(upload);
      expect(apiClient.post).toHaveBeenCalledWith(
        "/documents/records/",
        upload
      );

      await documentsService.replaceRecord(TEMPLATE, upload);
      expect(apiClient.post).toHaveBeenCalledWith(
        `/documents/records/${TEMPLATE}/versions/`,
        upload
      );

      await documentsService.verifyRecord(TEMPLATE);
      expect(apiClient.post).toHaveBeenCalledWith(
        `/documents/records/${TEMPLATE}/verify/`
      );
    });
  });

  describe("attendanceService", () => {
    test("parametros de jornada y movimientos", async () => {
      await attendanceService.listJornadaParameters({ page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/attendance/jornada-parameters/?page=1"
      );

      await attendanceService.createEvent({ student_id: STUDENT });
      expect(apiClient.post).toHaveBeenCalledWith("/attendance/events/", {
        student_id: STUDENT,
      });

      await attendanceService.listEvents();
      expect(apiClient.get).toHaveBeenCalledWith("/attendance/events/");
    });

    test("el estado del dia exige estudiante, jornada y fecha", async () => {
      await attendanceService.dayStatus({
        student_id: STUDENT,
        shift_id: SHIFT,
        event_date: "2026-08-06",
      });

      expect(apiClient.get).toHaveBeenCalledWith(
        `/attendance/day-status/?student_id=${STUDENT}&shift_id=${SHIFT}&event_date=2026-08-06`
      );
    });

    test("resolucion de movimiento y cierre de jornada", async () => {
      await attendanceService.eventResolution({
        student_id: STUDENT,
        shift_id: SHIFT,
        event_date: "2026-08-06",
        movement_type: "entry",
      });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/attendance/events/resolution/?student_id=${STUDENT}&shift_id=${SHIFT}&event_date=2026-08-06&movement_type=entry`
      );

      await attendanceService.closeJornada({ shift_id: SHIFT });
      expect(apiClient.post).toHaveBeenCalledWith(
        "/attendance/jornada-closures/",
        { shift_id: SHIFT }
      );

      await attendanceService.previewSectionClosure({
        section_id: "section-1",
      });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/attendance/section-closures/preview/?section_id=section-1"
      );

      await attendanceService.closeSection({ section_id: "section-1" });
      expect(apiClient.post).toHaveBeenCalledWith(
        "/attendance/section-closures/",
        { section_id: "section-1" }
      );

      await attendanceService.listAlerts();
      expect(apiClient.get).toHaveBeenCalledWith("/attendance/alerts/");

      await attendanceService.createJornadaParameters({ shift_id: SHIFT });
      expect(apiClient.post).toHaveBeenCalledWith(
        "/attendance/jornada-parameters/",
        { shift_id: SHIFT }
      );
    });
  });

  describe("evaluationService", () => {
    test("configuracion global y por ciclo son endpoints separados", async () => {
      await evaluationService.getGlobalConfig();
      expect(apiClient.get).toHaveBeenCalledWith(
        "/academics/evaluation-config/"
      );

      await evaluationService.updateGlobalConfig({ default_unit_count: 4 });
      expect(apiClient.patch).toHaveBeenCalledWith(
        "/academics/evaluation-config/",
        { default_unit_count: 4 }
      );

      await evaluationService.getCycleConfig(CYCLE);
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-config/`
      );

      await evaluationService.updateCycleConfig(CYCLE, { unit_count: 5 });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-config/`,
        { unit_count: 5 }
      );
    });

    test("unidades, ventana de recuperacion y excepciones cuelgan del ciclo", async () => {
      await evaluationService.listUnits(CYCLE, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-units/?page=1`
      );

      await evaluationService.createUnit(CYCLE, { number: 1 });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-units/`,
        { number: 1 }
      );

      await evaluationService.updateRecoveryWindow(CYCLE, UNIT, {
        recovery_starts_on: "2026-09-01",
      });
      expect(apiClient.patch).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-units/${UNIT}/recovery-window/`,
        { recovery_starts_on: "2026-09-01" }
      );

      await evaluationService.listCaptureExceptions(CYCLE, UNIT, { page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-units/${UNIT}/capture-exceptions/?page=1`
      );

      await evaluationService.createCaptureException(CYCLE, UNIT, {
        reason: "Incapacidad medica",
      });
      expect(apiClient.post).toHaveBeenCalledWith(
        `/academics/cycles/${CYCLE}/evaluation-units/${UNIT}/capture-exceptions/`,
        { reason: "Incapacidad medica" }
      );
    });
  });

  describe("reportingService", () => {
    test("acknowledged=false SI viaja: es la consulta util del tablero", async () => {
      // A diferencia del resto de la API, aqui `false` es significativo: pide
      // justamente lo que falta atender. Por eso el servicio desactiva el
      // descarte de booleanos en falso.
      await reportingService.listAlerts({ acknowledged: false });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/reporting/alerts/?acknowledged=false"
      );
    });

    test("filtra por tipo de alerta", async () => {
      await reportingService.listAlerts({ alert_type: "frecuencia_ausencias" });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/reporting/alerts/?alert_type=frecuencia_ausencias"
      );
    });

    test("atender, recalcular y umbrales", async () => {
      await reportingService.acknowledge(ALERT);
      expect(apiClient.post).toHaveBeenCalledWith(
        `/reporting/alerts/${ALERT}/acknowledge/`,
        {}
      );

      await reportingService.evaluate({
        shift_id: SHIFT,
        event_date: "2026-08-06",
      });
      expect(apiClient.post).toHaveBeenCalledWith(
        "/reporting/alert-evaluations/",
        { shift_id: SHIFT, event_date: "2026-08-06" }
      );

      await reportingService.listAbsenceThresholds({ page: 1 });
      expect(apiClient.get).toHaveBeenCalledWith(
        "/reporting/absence-threshold-parameters/?page=1"
      );

      await reportingService.createAbsenceThreshold({ max_absences: 3 });
      expect(apiClient.post).toHaveBeenCalledWith(
        "/reporting/absence-threshold-parameters/",
        { max_absences: 3 }
      );
    });
  });
});
