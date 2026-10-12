import { apiClient } from "@shared/api/apiClient.js";
import { collectAllPages } from "@shared/api/pages.js";
import { withQuery } from "@shared/api/query.js";

export const guardiansService = {
  /** Pagina cruda del listado, con su `count` total. */
  listPage: (params) =>
    apiClient.get(withQuery("/students/guardians/", params)),
  // Ver studentsService.list: la pantalla pagina del lado del cliente y
  // necesita la lista completa, no la primera pagina.
  list: () => collectAllPages(guardiansService.listPage),
  get: (id) => apiClient.get(`/students/guardians/${id}/`),
  create: (data) => apiClient.post("/students/guardians/", data),
  // GuardianSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/students/api/serializers.py), so name/email/phone
  // edits go to /people/<public_id>/ — Guardian has no other own field to patch.
  update: async (id, { person }) => {
    if (person) {
      const { public_id: personPublicId, ...personData } = person;
      await apiClient.patch(`/people/${personPublicId}/`, personData);
    }
    return guardiansService.get(id);
  },
};
