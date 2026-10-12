import { useCallback, useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import { guardiansService } from "@guardians/guardiansService.js";
import { studentsService } from "@students/studentsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useLocalList } from "@shared/crud/useLocalList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { ImageDialog } from "@ui/display/ImageDialog.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const STUDENT_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  {
    name: "cui",
    label: "CUI",
    required: true,
    help: "13 dígitos, sin guiones.",
  },
  {
    name: "birth_date",
    label: "Fecha de nacimiento",
    type: "date",
    required: true,
  },
  {
    name: "sex",
    label: "Sexo",
    type: "select",
    required: true,
    options: [
      { value: "female", label: "Femenino" },
      { value: "male", label: "Masculino" },
    ],
  },
  { name: "nationality", label: "Nacionalidad", required: true },
  { name: "phone_number", label: "Teléfono", type: "tel", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "address", label: "Dirección", required: true, span: "full" },
  { name: "department", label: "Departamento", required: true },
  { name: "municipality", label: "Municipio", required: true },
  {
    name: "student_code",
    label: "Codigo de estudiante",
    help: "Se genera solo. Cambielo si el expediente ya trae uno asignado.",
  },
  {
    name: "photo",
    label: "Foto tamaño cédula (295 × 354 px, máximo 5 MB)",
    type: "file",
    accept: "image/*",
  },
];

/** Estados de expediente del estudiante, tal como los expone el backend. */
const STATUS_LABEL = {
  pre_enrolled: "Preinscrito",
  active: "Activo",
  inactive: "Inactivo",
  withdrawn: "Retirado",
  graduated: "Graduado",
};

const STATUS_OPTIONS = Object.entries(STATUS_LABEL).map(([value, label]) => ({
  value,
  label,
}));

const STUDENT_EDIT_FIELDS = [
  ...STUDENT_FIELDS.filter(
    (field) => field.name !== "cui" && field.name !== "birth_date"
  ),
  {
    name: "status",
    label: "Estado",
    type: "select",
    required: true,
    options: STATUS_OPTIONS,
  },
];

/** Estados de expediente del estudiante -> variante semantica de chip. */
const STATUS_VARIANT = {
  active: "success",
  pre_enrolled: "primary",
  inactive: "neutral",
  withdrawn: "danger",
  graduated: "purple",
};

function fullName(student) {
  return `${student.person.first_name} ${student.person.last_name}`.trim();
}

function personPayload(values) {
  return Object.fromEntries(
    Object.entries({
      first_name: values.first_name,
      last_name: values.last_name,
      cui: values.cui,
      birth_date: values.birth_date,
      sex: values.sex,
      nationality: values.nationality,
      phone_number: values.phone_number,
      email: values.email,
      address: values.address,
      department: values.department,
      municipality: values.municipality,
    }).filter(([, value]) => value !== "" && value != null)
  );
}

export function AlumnosPage() {
  const loadStudents = useCallback(() => studentsService.list(), []);
  const matches = useCallback(
    (student, query) => fullName(student).toLowerCase().includes(query),
    []
  );
  const list = useLocalList(loadStudents, { matches });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  // Guarda los valores iniciales, no un booleano: el codigo sugerido se pide al
  // abrir para que ya este puesto al montar el formulario. Un campo que cambia
  // solo, despues, debajo de quien escribe, es peor que uno vacio.
  const [creating, setCreating] = useState(null);
  const [viewingPhoto, setViewingPhoto] = useState(null);
  const [healthOpen, setHealthOpen] = useState(false);
  const [healthNotes, setHealthNotes] = useState([]);
  const [healthError, setHealthError] = useState("");
  const [creatingHealthNote, setCreatingHealthNote] = useState(false);
  const [observationsOpen, setObservationsOpen] = useState(false);
  const [observations, setObservations] = useState([]);
  const [observationError, setObservationError] = useState("");
  const [creatingObservation, setCreatingObservation] = useState(false);
  const [emergencyContactsOpen, setEmergencyContactsOpen] = useState(false);
  const [emergencyContacts, setEmergencyContacts] = useState([]);
  const [emergencyContactError, setEmergencyContactError] = useState("");
  const [creatingEmergencyContact, setCreatingEmergencyContact] =
    useState(false);

  const openHealth = async () => {
    setHealthError("");
    try {
      setHealthNotes(await studentsService.listHealthNotes(selected.public_id));
      setHealthOpen(true);
    } catch (error) {
      setHealthError(error.message);
    }
  };

  const handleCreateHealthNote = async (values) => {
    const created = await studentsService.createHealthNote(
      selected.public_id,
      values
    );
    setHealthNotes((current) => [created, ...current]);
    setCreatingHealthNote(false);
  };

  const openObservations = async () => {
    setObservationError("");
    try {
      setObservations(
        await studentsService.listObservations(selected.public_id)
      );
      setObservationsOpen(true);
    } catch (error) {
      setObservationError(error.message);
    }
  };

  const handleCreateObservation = async (values) => {
    const created = await studentsService.createObservation(
      selected.public_id,
      values
    );
    setObservations((current) => [created, ...current]);
    setCreatingObservation(false);
  };

  const openEmergencyContacts = async () => {
    setEmergencyContactError("");
    try {
      setEmergencyContacts(
        await studentsService.listEmergencyContacts(selected.public_id)
      );
      setEmergencyContactsOpen(true);
    } catch (error) {
      setEmergencyContactError(error.message);
    }
  };

  const handleCreateEmergencyContact = async (values) => {
    const created = await studentsService.createEmergencyContact(
      selected.public_id,
      values
    );
    setEmergencyContacts((current) => [created, ...current]);
    setCreatingEmergencyContact(false);
  };

  const [guardianRelations, setGuardianRelations] = useState([]);
  const [availableGuardians, setAvailableGuardians] = useState([]);
  const [linkingGuardian, setLinkingGuardian] = useState(false);
  const [guardianError, setGuardianError] = useState("");

  const handleSelect = async (student) => {
    setSelected(student);
    setGuardianRelations([]);
    setGuardianError("");
    try {
      const relations = await studentsService.listGuardianRelations();
      setGuardianRelations(
        relations.filter((relation) => relation.student === student.id)
      );
    } catch (error) {
      setGuardianError(error.message);
    }
  };

  const openGuardianLink = async () => {
    setGuardianError("");
    try {
      setAvailableGuardians(await guardiansService.list());
      setLinkingGuardian(true);
    } catch (error) {
      setGuardianError(error.message);
    }
  };

  const handleGuardianLink = async (values) => {
    const created = await studentsService.createGuardianRelation({
      student: selected.id,
      guardian: Number(values.guardian),
      relationship_label: values.relationship_label,
    });
    setGuardianRelations((current) => [...current, created]);
    setLinkingGuardian(false);
  };

  const handleExport = () => {
    downloadCsv(
      "alumnos.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Codigo", value: (item) => item.student_code },
        {
          label: "Estado",
          value: (item) => STATUS_LABEL[item.status] ?? item.status,
        },
      ],
      list.filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await studentsService.create({
      person: personPayload(values),
      student_code: values.student_code,
      status: "pre_enrolled",
      photo: values.photo,
    });
    list.addItem(created);
    setCreating(null);
  };

  const handleUpdate = async (values) => {
    const updated = await studentsService.update(editing.id, {
      person: {
        id: editing.person.public_id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      student_code: values.student_code,
      status: values.status,
      photo: values.photo,
    });
    list.replaceItem(updated, (item) => item.id === updated.id);
    setSelected(updated);
    setEditing(null);
  };

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (student) =>
        student.photo ? (
          <Avatar
            src={student.photo}
            sx={{ width: 32, height: 32 }}
            variant="rounded"
          />
        ) : (
          <Avatar sx={{ width: 32, height: 32 }} variant="rounded">
            <PersonOutlineIcon fontSize="small" />
          </Avatar>
        ),
    },
    { key: "nombre", label: "Nombre completo", render: fullName },
    {
      key: "codigo",
      label: "Codigo",
      render: (student) => student.student_code,
    },
    {
      key: "estado",
      label: "Estado",
      render: (student) => (
        <StatusChip
          label={STATUS_LABEL[student.status] ?? student.status}
          variant={STATUS_VARIANT[student.status] ?? "neutral"}
        />
      ),
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (student) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(student)}`}
          onClick={() => handleSelect(student)}
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={async () =>
              setCreating({
                ...EMPTY_STUDENT,
                student_code: await suggestedOrBlank(studentsService.nextCode),
              })
            }
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo estudiante
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={`${list.filtered.length} de ${list.all.length} registros dentro de tu alcance.`}
        title="Estudiantes"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <Button
              onClick={handleExport}
              size="small"
              startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Exportar CSV
            </Button>
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre…"
            value={list.search}
          />
        </FilterBar>

        {list.error ? (
          <Alert
            role="alert"
            severity="error"
            sx={{ mx: { xs: 1.5, md: 2 }, mt: 1.5 }}
          >
            {list.error}
          </Alert>
        ) : null}

        <SectionTableArea>
          <DataTable
            columns={columns}
            emptyMessage={
              list.search
                ? "Sin resultados para la busqueda."
                : "Todavia no hay estudiantes registrados."
            }
            fillHeight
            loading={list.loading}
            onRowClick={handleSelect}
            pagination={list.pagination}
            rows={list.items}
          />
        </SectionTableArea>
      </SectionCard>

      <DetailWindow
        actions={
          selected ? (
            <Stack direction="row" gap={1}>
              <Button onClick={openHealth} variant="outlined">
                Salud
              </Button>
              <Button onClick={openObservations} variant="outlined">
                Observaciones
              </Button>
              <Button onClick={openEmergencyContacts} variant="outlined">
                Contactos de emergencia
              </Button>
              <Button onClick={openGuardianLink} variant="outlined">
                Vincular encargado
              </Button>
              <Button onClick={() => setEditing(selected)} variant="contained">
                Editar
              </Button>
            </Stack>
          ) : null
        }
        fields={
          selected
            ? [
                { label: "Nombre completo", value: fullName(selected) },
                { label: "Codigo de estudiante", value: selected.student_code },
                {
                  label: "Estado",
                  value: (
                    <StatusChip
                      label={STATUS_LABEL[selected.status] ?? selected.status}
                      variant={STATUS_VARIANT[selected.status] ?? "neutral"}
                    />
                  ),
                },
                { label: "Correo", value: selected.person.email },
                { label: "Telefono", value: selected.person.phone_number },
                {
                  label: "Foto",
                  value: selected.photo ? (
                    <ButtonBase
                      onClick={() => setViewingPhoto(selected.photo)}
                      sx={(theme) => ({
                        borderRadius: theme.tokens.radii.chip,
                        mt: 0.5,
                      })}
                    >
                      <Box
                        alt={`Foto de ${fullName(selected)}`}
                        component="img"
                        src={selected.photo}
                        sx={(theme) => ({
                          width: 112,
                          height: 112,
                          objectFit: "cover",
                          borderRadius: theme.tokens.radii.chip,
                          border: "1px solid",
                          borderColor: "divider",
                        })}
                      />
                    </ButtonBase>
                  ) : (
                    <MutedCell>Sin foto</MutedCell>
                  ),
                },
                {
                  label: "Encargados",
                  value: guardianError ? (
                    <Alert severity="error">{guardianError}</Alert>
                  ) : guardianRelations.length ? (
                    <Stack gap={0.75}>
                      {guardianRelations.map((relation) => (
                        <Box key={relation.id}>
                          <Typography fontWeight={600} variant="body2">
                            {fullName(relation.guardian_detail)}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            {relation.relationship_label}
                            {relation.is_primary ? " · Principal" : ""}
                            {relation.ends_at ? " · Finalizado" : ""}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  ) : (
                    <MutedCell>Sin encargados vinculados</MutedCell>
                  ),
                },
              ]
            : []
        }
        onClose={() => {
          setSelected(null);
          setViewingPhoto(null);
          setHealthOpen(false);
          setHealthNotes([]);
          setHealthError("");
          setObservationsOpen(false);
          setObservations([]);
          setObservationError("");
          setEmergencyContactsOpen(false);
          setEmergencyContacts([]);
          setEmergencyContactError("");
          setGuardianRelations([]);
          setGuardianError("");
        }}
        open={Boolean(selected)}
        title={selected ? fullName(selected) : ""}
      />

      <DetailWindow
        actions={
          <Button
            onClick={() => setCreatingHealthNote(true)}
            variant="contained"
          >
            Nueva nota
          </Button>
        }
        fields={[
          {
            label: "Notas de salud",
            value: healthError ? (
              <Alert severity="error">{healthError}</Alert>
            ) : healthNotes.length ? (
              <Stack gap={1}>
                {healthNotes.map((note) => (
                  <Box key={note.public_id}>
                    <Typography fontWeight={600} variant="body2">
                      {note.recorded_on} · {note.author}
                    </Typography>
                    <Typography variant="body2">{note.content}</Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <MutedCell>Sin notas de salud</MutedCell>
            ),
          },
        ]}
        onClose={() => setHealthOpen(false)}
        open={healthOpen}
        title={selected ? `Salud de ${fullName(selected)}` : "Salud"}
      />

      <EntityFormWindow
        fields={[
          { name: "content", label: "Información de salud", required: true },
        ]}
        initialValues={{ content: "" }}
        key={creatingHealthNote ? `health-${selected?.id}` : "health-closed"}
        onCancel={() => setCreatingHealthNote(false)}
        onSubmit={handleCreateHealthNote}
        open={creatingHealthNote}
        submitLabel="Registrar nota"
        title="Nueva nota de salud"
      />

      <DetailWindow
        actions={
          <Button
            onClick={() => setCreatingObservation(true)}
            variant="contained"
          >
            Nueva observación
          </Button>
        }
        fields={[
          {
            label: "Observaciones sensibles",
            value: observationError ? (
              <Alert severity="error">{observationError}</Alert>
            ) : observations.length ? (
              <Stack gap={1}>
                {observations.map((observation) => (
                  <Box key={observation.public_id}>
                    <Typography fontWeight={600} variant="body2">
                      {observation.observed_on} · {observation.author}
                    </Typography>
                    <Typography variant="body2">
                      {observation.description}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <MutedCell>Sin observaciones</MutedCell>
            ),
          },
        ]}
        onClose={() => setObservationsOpen(false)}
        open={observationsOpen}
        title={
          selected ? `Observaciones de ${fullName(selected)}` : "Observaciones"
        }
      />

      <EntityFormWindow
        fields={[{ name: "description", label: "Descripción", required: true }]}
        initialValues={{ description: "" }}
        key={
          creatingObservation
            ? `observation-${selected?.id}`
            : "observation-closed"
        }
        onCancel={() => setCreatingObservation(false)}
        onSubmit={handleCreateObservation}
        open={creatingObservation}
        submitLabel="Registrar observación"
        title="Nueva observación"
      />

      <DetailWindow
        actions={
          <Button
            onClick={() => setCreatingEmergencyContact(true)}
            variant="contained"
          >
            Nuevo contacto
          </Button>
        }
        fields={[
          {
            label: "Contactos de emergencia",
            value: emergencyContactError ? (
              <Alert severity="error">{emergencyContactError}</Alert>
            ) : emergencyContacts.length ? (
              <Stack gap={1}>
                {emergencyContacts.map((contact) => (
                  <Box key={contact.public_id}>
                    <Typography fontWeight={600} variant="body2">
                      {contact.name} · {contact.relationship_label}
                    </Typography>
                    <Typography variant="body2">
                      {contact.phone_number}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <MutedCell>Sin contactos de emergencia</MutedCell>
            ),
          },
        ]}
        onClose={() => setEmergencyContactsOpen(false)}
        open={emergencyContactsOpen}
        title={selected ? `Contactos de ${fullName(selected)}` : "Contactos"}
      />

      <EntityFormWindow
        fields={[
          { name: "name", label: "Nombre", required: true },
          { name: "phone_number", label: "Teléfono", required: true },
          {
            name: "relationship_label",
            label: "Relación",
            required: true,
          },
        ]}
        initialValues={{ name: "", phone_number: "", relationship_label: "" }}
        key={
          creatingEmergencyContact
            ? `emergency-contact-${selected?.id}`
            : "emergency-contact-closed"
        }
        onCancel={() => setCreatingEmergencyContact(false)}
        onSubmit={handleCreateEmergencyContact}
        open={creatingEmergencyContact}
        submitLabel="Registrar contacto"
        title="Nuevo contacto de emergencia"
      />

      <ImageDialog
        alt={selected ? fullName(selected) : ""}
        downloadName={viewingPhoto?.split("/").pop()}
        onClose={() => setViewingPhoto(null)}
        open={Boolean(viewingPhoto)}
        src={viewingPhoto ?? ""}
      />

      {creating ? (
        <EntityFormWindow
          description="El codigo se emite solo; el resto es lo que hay que capturar."
          fields={STUDENT_FIELDS}
          initialValues={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear estudiante"
          title="Nuevo estudiante"
        />
      ) : null}

      {editing ? (
        <EntityFormWindow
          fields={STUDENT_EDIT_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            sex: editing.person.sex ?? "",
            nationality: editing.person.nationality ?? "",
            email: editing.person.email ?? "",
            phone_number: editing.person.phone_number ?? "",
            address: editing.person.address ?? "",
            department: editing.person.department ?? "",
            municipality: editing.person.municipality ?? "",
            student_code: editing.student_code,
            status: editing.status,
            photo: null,
          }}
          key={editing.id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${fullName(editing)}`}
        />
      ) : null}

      <EntityFormWindow
        fields={[
          {
            name: "guardian",
            label: "Encargado",
            type: "select",
            required: true,
            // El correo entra en la etiqueta porque dos encargados pueden
            // llamarse igual, y en un desplegable de nombres repetidos no hay
            // forma de saber cual se esta eligiendo.
            options: availableGuardians.map((guardian) => ({
              value: guardian.id,
              label: [fullName(guardian), guardian.person?.email]
                .filter(Boolean)
                .join(" · "),
            })),
          },
          {
            name: "relationship_label",
            label: "Parentesco o responsabilidad",
            required: true,
          },
        ]}
        initialValues={{ guardian: "", relationship_label: "" }}
        key={linkingGuardian ? `guardian-${selected?.id}` : "guardian-closed"}
        onCancel={() => setLinkingGuardian(false)}
        onSubmit={handleGuardianLink}
        open={linkingGuardian}
        submitLabel="Vincular encargado"
        title="Vincular encargado"
      />
    </>
  );
}

const EMPTY_STUDENT = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  cui: "",
  birth_date: "",
  sex: "",
  nationality: "Guatemalteca",
  address: "",
  department: "",
  municipality: "",
  student_code: "",
  photo: null,
};
