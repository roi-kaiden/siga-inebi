import { apiClient } from "@shared/api/apiClient.js";
import { collectAllPages } from "@shared/api/pages.js";
import { withQuery } from "@shared/api/query.js";

export const teachersService = {
  /** Pagina cruda del listado. La usan los selectores, que recorren todas. */
  listPage: (params) => apiClient.get(withQuery("/teachers/", params)),
  // Ver studentsService.list: la pantalla pagina del lado del cliente y
  // necesita la lista completa, no la primera pagina.
  list: () => collectAllPages(teachersService.listPage),
  get: (id) => apiClient.get(`/teachers/${id}/`),
  /** Siguiente codigo de empleado libre. Ver `studentsService.nextCode`. */
  nextCode: () =>
    apiClient.get("/teachers/next-code/").then((body) => body.employee_code),
  create: async ({ photo, ...data }) => {
    const created = await apiClient.post("/teachers/", data);
    if (!photo) {
      return created;
    }
    const formData = new FormData();
    formData.append("photo", photo);
    return apiClient.patch(`/teachers/${created.id}/`, formData);
  },
  // TeacherSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/teachers/api/serializers.py), so name/email/phone
  // edits go to /people/<public_id>/ while employee_code/specialty/position/photo
  // go to /teachers/<id>/ — the same two-endpoint split used by create.
  update: async (id, { photo, person, ...data }) => {
    if (person) {
      const { public_id: personPublicId, ...personData } = person;
      await apiClient.patch(`/people/${personPublicId}/`, personData);
    }
    if (Object.keys(data).length > 0) {
      await apiClient.patch(`/teachers/${id}/`, data);
    }
    if (photo) {
      const formData = new FormData();
      formData.append("photo", photo);
      await apiClient.patch(`/teachers/${id}/`, formData);
    }
    return teachersService.get(id);
  },
};
