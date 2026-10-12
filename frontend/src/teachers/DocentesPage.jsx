import { useCallback, useMemo, useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import { POSITION_OPTIONS } from "@teachers/teachersMock.js";
import { teachersService } from "@teachers/teachersService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useLocalList } from "@shared/crud/useLocalList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { formatDate } from "@shared/utils/format.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { ImageDialog } from "@ui/display/ImageDialog.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const TEACHER_FIELDS = [
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
  { name: "specialty", label: "Especialidad", required: true },
  {
    name: "position",
    label: "Puesto",
    type: "select",
    options: POSITION_OPTIONS,
    required: true,
  },
  {
    name: "appointment_date",
    label: "Fecha de nombramiento (opcional)",
    type: "date",
  },
  {
    name: "employee_code",
    label: "Codigo de empleado",
    help: "Se genera solo. Cambielo si ya figura en contratos o planilla.",
  },
  { name: "photo", label: "Foto (opcional)", type: "file", accept: "image/*" },
];

const ALL_POSITIONS = "";

const TEACHER_EDIT_FIELDS = TEACHER_FIELDS.filter(
  (field) => field.name !== "cui" && field.name !== "birth_date"
);

const POSITION_FILTER_OPTIONS = [
  { value: ALL_POSITIONS, label: "Todos los puestos" },
  ...POSITION_OPTIONS.map((option) => ({ value: option, label: option })),
];

function fullName(teacher) {
  return `${teacher.person.first_name} ${teacher.person.last_name}`.trim();
}

const personPayload = (values) => ({
  ...Object.fromEntries(
    Object.entries({
      first_name: values.first_name,
      last_name: values.last_name,
      cui: values.cui,
      birth_date: values.birth_date,
      sex: values.sex,
      nationality: values.nationality,
      email: values.email,
      phone_number: values.phone_number,
      address: values.address,
      department: values.department,
      municipality: values.municipality,
    }).filter(([, value]) => value !== "" && value != null)
  ),
});

export function DocentesPage() {
  const [positionFilter, setPositionFilter] = useState(ALL_POSITIONS);

  const loadTeachers = useCallback(() => teachersService.list(), []);
  const matches = useCallback(
    (teacher, query) => fullName(teacher).toLowerCase().includes(query),
    []
  );
  // Memorizado porque `useLocalList` lo usa como dependencia del filtrado: una
  // funcion nueva en cada render recalcularia la lista sin necesidad.
  const filters = useMemo(
    () =>
      positionFilter
        ? (teacher) => teacher.position === positionFilter
        : undefined,
    [positionFilter]
  );

  const list = useLocalList(loadTeachers, { filters, matches });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  // Valores iniciales, no un booleano: ver el comentario homonimo en
  // AlumnosPage. El codigo sugerido se pide al abrir.
  const [creating, setCreating] = useState(null);
  const [viewingPhoto, setViewingPhoto] = useState(null);

  const handleExport = () => {
    downloadCsv(
      "docentes.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Especialidad", value: (item) => item.specialty },
        { label: "Puesto", value: (item) => item.position },
        { label: "Codigo Empleado", value: (item) => item.employee_code },
      ],
      list.filtered
    );
  };

  const buildPayload = (values) => ({
    person: personPayload(values),
    employee_code: values.employee_code,
    specialty: values.specialty,
    position: values.position,
    appointment_date: values.appointment_date || null,
    photo: values.photo,
  });

  const handleCreate = async (values) => {
    const created = await teachersService.create(buildPayload(values));
    list.addItem(created);
    setCreating(null);
  };

  const handleUpdate = async (values) => {
    const updated = await teachersService.update(editing.id, {
      ...buildPayload(values),
      person: {
        id: editing.person.public_id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
    });
    list.replaceItem(updated, (item) => item.id === updated.id);
    setSelected(updated);
    setEditing(null);
  };

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (teacher) =>
        teacher.photo ? (
          <Avatar
            src={teacher.photo}
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
      key: "especialidad",
      label: "Especialidad",
      render: (item) => item.specialty,
    },
    {
      key: "puesto",
      label: "Puesto",
      render: (item) => <StatusChip label={item.position} variant="primary" />,
    },
    {
      key: "codigo",
      label: "Codigo empleado",
      render: (item) => item.employee_code,
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (teacher) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(teacher)}`}
          onClick={() => setSelected(teacher)}
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
                ...EMPTY_TEACHER,
                employee_code: await suggestedOrBlank(teachersService.nextCode),
              })
            }
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo registro
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={`${list.filtered.length} de ${list.all.length} registros de personal docente y administrativo.`}
        title="Docentes y administrativos"
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
          onClear={
            list.search || positionFilter
              ? () => {
                  list.setSearch("");
                  setPositionFilter(ALL_POSITIONS);
                }
              : undefined
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre…"
            value={list.search}
          />
          <FilterSelect
            label="Filtrar por puesto"
            minWidth={190}
            onChange={setPositionFilter}
            options={POSITION_FILTER_OPTIONS}
            value={positionFilter}
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
              list.search || positionFilter
                ? "Sin datos para los filtros seleccionados."
                : "Todavia no hay personal registrado."
            }
            fillHeight
            loading={list.loading}
            onRowClick={setSelected}
            pagination={list.pagination}
            rows={list.items}
          />
        </SectionTableArea>
      </SectionCard>

      <DetailWindow
        actions={
          selected ? (
            <Button onClick={() => setEditing(selected)} variant="contained">
              Editar
            </Button>
          ) : null
        }
        fields={
          selected
            ? [
                { label: "Nombre completo", value: fullName(selected) },
                { label: "Especialidad", value: selected.specialty },
                {
                  label: "Puesto",
                  value: (
                    <StatusChip label={selected.position} variant="primary" />
                  ),
                },
                { label: "Codigo de empleado", value: selected.employee_code },
                {
                  label: "Fecha de nombramiento",
                  value: selected.appointment_date
                    ? formatDate(selected.appointment_date)
                    : null,
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
              ]
            : []
        }
        onClose={() => {
          setSelected(null);
          setViewingPhoto(null);
        }}
        open={Boolean(selected)}
        title={selected ? fullName(selected) : ""}
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
          description="El codigo de empleado se emite solo; el resto es lo que hay que capturar."
          fields={TEACHER_FIELDS}
          initialValues={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear registro"
          title="Nuevo docente o administrativo"
        />
      ) : null}

      {editing ? (
        <EntityFormWindow
          fields={TEACHER_EDIT_FIELDS}
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
            specialty: editing.specialty,
            position: editing.position,
            appointment_date: editing.appointment_date ?? "",
            employee_code: editing.employee_code,
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
    </>
  );
}

const EMPTY_TEACHER = {
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
  specialty: "",
  position: "",
  appointment_date: "",
  employee_code: "",
  photo: null,
};
