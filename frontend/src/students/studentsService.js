import { apiClient } from "@shared/api/apiClient.js";
import { collectAllPages } from "@shared/api/pages.js";
import { withQuery } from "@shared/api/query.js";

export const studentsService = {
  /** Pagina cruda del listado. La usan los selectores, que recorren todas. */
  listPage: (params) => apiClient.get(withQuery("/students/", params)),
  // AlumnosPage pagina, busca y exporta del lado del cliente, asi que necesita
  // la lista completa: con solo la primera pagina su paginador anunciaba
  // "25 de 25" y el resto de los estudiantes no existia para quien buscaba.
  list: () => collectAllPages(studentsService.listPage),
  get: (id) => apiClient.get(`/students/${id}/`),
  /**
   * Siguiente codigo de estudiante libre, para prellenar el alta.
   *
   * Es el MISMO que asignaria el backend si el campo llegara vacio; no reserva
   * nada, asi que dos formularios abiertos a la vez ven el mismo valor y el
   * segundo que guarde recibe el siguiente.
   */
  nextCode: () =>
    apiClient.get("/students/next-code/").then((body) => body.student_code),
  listHealthNotes: (studentPublicId) =>
    apiClient
      .get(`/students/${studentPublicId}/health-notes/`)
      .then((page) => page.results),
  createHealthNote: (studentPublicId, data) =>
    apiClient.post(`/students/${studentPublicId}/health-notes/`, data),
  listObservations: (studentPublicId) =>
    apiClient
      .get(`/students/${studentPublicId}/observations/`)
      .then((page) => page.results),
  createObservation: (studentPublicId, data) =>
    apiClient.post(`/students/${studentPublicId}/observations/`, data),
  listEmergencyContacts: (studentPublicId) =>
    apiClient
      .get(`/students/${studentPublicId}/emergency-contacts/`)
      .then((page) => page.results),
  createEmergencyContact: (studentPublicId, data) =>
    apiClient.post(`/students/${studentPublicId}/emergency-contacts/`, data),
  listGuardianRelations: () =>
    apiClient.get("/students/guardian-relations/").then((page) => page.results),
  createGuardianRelation: (data) =>
    apiClient.post("/students/guardian-relations/", data),
  create: async ({ photo, ...data }) => {
    const created = await apiClient.post("/students/", data);
    if (!photo) {
      return created;
    }
    const formData = new FormData();
    formData.append("photo", photo);
    return apiClient.patch(`/students/${created.id}/`, formData);
  },
  // StudentSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/students/api/serializers.py), so name/email/phone
  // edits go to /people/<public_id>/ while student_code/photo go to
  // /students/<id>/ — the same two-endpoint split used by create.
  update: async (id, { photo, person, ...data }) => {
    if (person) {
      const { public_id: personPublicId, ...personData } = person;
      await apiClient.patch(`/people/${personPublicId}/`, personData);
    }
    if (Object.keys(data).length > 0) {
      await apiClient.patch(`/students/${id}/`, data);
    }
    if (photo) {
      const formData = new FormData();
      formData.append("photo", photo);
      await apiClient.patch(`/students/${id}/`, formData);
    }
    return studentsService.get(id);
  },
};
