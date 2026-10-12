import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

const PILLARS = [
  {
    title: "Base actual",
    body: "Monolito modular con Django REST Framework, React, PostgreSQL y controles de autorizacion por rol y alcance.",
  },
  {
    title: "Enfoque",
    body: "Denegacion por defecto, cuentas institucionales vinculadas a personas, auditoria y compatibilidad con desarrollo local o Docker.",
  },
];

export function HomePage() {
  return (
    <Stack gap={3}>
      <SectionCard>
        <Box sx={{ px: { xs: 3, md: 5 }, py: { xs: 4, md: 5 } }}>
          <Typography
            component="p"
            sx={{ color: "primary.main" }}
            variant="overline"
          >
            Sistema institucional
          </Typography>
          <Typography sx={{ mt: 1, maxWidth: "34ch" }} variant="h4">
            Control academico, administrativo y operativo en una sola base
            segura.
          </Typography>
          <Typography
            color="text.secondary"
            sx={{ mt: 2, maxWidth: "62ch" }}
            variant="body1"
          >
            SIGA-INEBI centraliza acceso, estudiantes, estructura academica,
            matricula y trazabilidad con autenticacion institucional y API JSON.
          </Typography>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            gap={1.5}
            sx={{ mt: 3 }}
          >
            <Button component={RouterLink} to="/login" variant="contained">
              Ingresar al sistema
            </Button>
          </Stack>
        </Box>
      </SectionCard>

      <Grid container spacing={2}>
        {PILLARS.map((pillar) => (
          <Grid key={pillar.title} size={{ xs: 12, md: 6 }}>
            <SectionCard
              marker={false}
              sx={{ height: "100%" }}
              title={pillar.title}
            >
              <Typography
                color="text.secondary"
                sx={{ px: 3, py: 2.5 }}
                variant="body2"
              >
                {pillar.body}
              </Typography>
            </SectionCard>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}
