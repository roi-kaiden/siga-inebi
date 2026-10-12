import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const resolvePath = (relative) =>
  fileURLToPath(new URL(relative, import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyTarget =
    env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    resolve: {
      // Alias por dominio. Un import se lee como una direccion del sistema
      // ("@students/...") en vez de como una ruta relativa que cambia cada vez
      // que un archivo se mueve de carpeta; mover un modulo deja de tocar los
      // imports de todos sus vecinos, que es donde nacen los conflictos de merge.
      alias: {
        "@": resolvePath("./src"),
        "@app": resolvePath("./src/app"),
        "@shared": resolvePath("./src/shared"),
        "@ui": resolvePath("./src/shared/ui"),
        "@layout": resolvePath("./src/shared/layout"),
        "@theme": resolvePath("./src/shared/theme"),
        "@auth": resolvePath("./src/auth"),
        "@dashboard": resolvePath("./src/dashboard"),
        "@people": resolvePath("./src/people"),
        "@students": resolvePath("./src/students"),
        "@teachers": resolvePath("./src/teachers"),
        "@guardians": resolvePath("./src/guardians"),
        "@academics": resolvePath("./src/academics"),
        "@cycles": resolvePath("./src/cycles"),
        "@enrolments": resolvePath("./src/enrolments"),
        "@attendance": resolvePath("./src/attendance"),
        "@evaluation": resolvePath("./src/evaluation"),
        "@documents": resolvePath("./src/documents"),
        "@reporting": resolvePath("./src/reporting"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        // changeOrigin is off on purpose: Django builds absolute media URLs
        // (e.g. student photos) from the inbound Host header. Rewriting it to
        // the backend's own docker-internal host would bake an unreachable
        // hostname into those URLs; keeping the original Host (as seen by the
        // browser) means the URLs it gets back are ones it can actually load.
        "/api": {
          target: backendProxyTarget,
          changeOrigin: false,
        },
        "/media": {
          target: backendProxyTarget,
          changeOrigin: false,
        },
      },
    },
    build: {
      // Keep graphics visible in the manifest so the static raster cap cannot
      // be bypassed by Vite's default small-asset inlining.
      assetsInlineLimit: 0,
      manifest: true,
      target: ["chrome107", "edge107", "firefox104", "safari16"],
      rollupOptions: {
        output: {
          // Chunks explicitos para las dependencias que no cambian: el usuario
          // los descarga una vez y sobreviven a cada despliegue del producto.
          // Sin esto, cualquier cambio de una pagina invalida MUI entero.
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router-dom"],
            "vendor-mui-core": ["@mui/material", "@mui/material/styles"],
            "vendor-emotion": ["@emotion/react", "@emotion/styled"],
            // Las ventanas bajo demanda de asistencia comparten estos modulos
            // con la pagina principal. Sin un limite explicito, Rollup los
            // asociaba al chunk de AttendancePage y una ventana terminaba
            // descargando codigo de la pagina que no utiliza.
            "attendance-shared": [
              resolvePath("./src/attendance/attendanceService.js"),
              resolvePath("./src/shared/catalogs/academicCatalogs.js"),
              resolvePath("./src/shared/utils/format.js"),
            ],
          },
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.js",
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
        include: ["src/**/*.{js,jsx}"],
        exclude: [
          "src/app/main.jsx",
          "src/shared/theme/**",
          "src/**/index.js",
          "src/test/**",
        ],
        thresholds: {
          lines: 60,
          functions: 60,
          branches: 50,
          statements: 60,
        },
      },
    },
  };
});
