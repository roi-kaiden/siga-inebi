# Ronda 10: consulta de resultado con red interrumpida

Corrida `RUN-EST-20261012-10`, 12 de octubre de 2026, sobre
`feaf30f232ec0b1189bb4dc917b523a5819c0140`, rama de la ronda 9 aún no
integrada en `develop`. Edge 155.0.4283.45 y Firefox 157.0 headless,
frontend Vite, Django 5.2.17 y PostgreSQL 16 aislado. Cuenta, matrícula,
ciclo y subárea sintéticos; no se registraron notas. Ejecución asistida de
Estuardo; revisión de Emilio y triage de Pablo pendientes.

## Procedimiento y resultado

Después del login y de elegir estudiante y subárea en «Consultar resultado»,
se cortó la red del contexto del navegador antes de pulsar «Consultar». Se
observó el mensaje de error y se verificó que el diálogo permanecía visible.
Luego se restableció la red y se repitió la consulta sin recargar la página.

| Navegador | Mensaje durante el corte | Reintento |
| --- | --- | --- |
| Edge | `Failed to fetch` | HTTP 200; «Sin calificar» visible; alerta eliminada |
| Firefox | `NetworkError when attempting to fetch resource.` | HTTP 200; «Sin calificar» visible; alerta eliminada |

**Resultado funcional:** la consulta se recuperó en ambos navegadores sin
reiniciar sesión ni recargar la pantalla. Esta consulta es de lectura; la
prueba no evalúa deduplicación de escrituras ni comportamiento offline de
asistencia.

**Hallazgo INC-009, propuesto para triage:** los errores de red se muestran en
inglés en una interfaz española y no indican al usuario que restablezca la
conexión y reintente. Afecta la comprensión práctica del error de la sección
10.5 del plan; la corrección y la severidad definitiva requieren revisión de
Emilio y Pablo. No se modificó el cliente API en esta ronda.

## Evidencia y límites

El JSON original, sin credenciales ni cookies, está excluido de Git en
`docs/quality/fase-7/evidence/RUN-EST-20261012-10/network-results.json`;
SHA-256 `D1CC450B0E934BF05D7E6D81792AEFFC673F3AA0E043E79FEE038171B48D9007`.
El script de ejecución permanece local en
`tmp/qa-browser/round10-network.cjs`; la secuencia anterior permite repetir
el caso. La red se interrumpió mediante Playwright en el navegador, no mediante
un corte físico de Wi-Fi. No hubo usuarios institucionales ni Android real;
esta corrida no constituye UAT ni cierra usabilidad.
