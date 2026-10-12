# Prueba de carga de escaneo (RNF-REN-001/002)

1. Sembrar datos sinteticos en el backend objetivo (solo entornos de prueba):
   `docker compose exec -T backend python manage.py shell < scripts/quality/load/seed_scan_load.py > seed.json`
2. Ejecutar: `python scripts/quality/load/scan_load_test.py --seed seed.json --operators 3 --requests-per-operator 50 --out result.json`
3. Pruebas del script: `cd scripts/quality/load && python -m unittest test_scan_load_test`

El exit code es 1 si p95 > 2 s o hay eventos fallidos/perdidos. Los resultados
describen solo el entorno medido (en local `runserver`, no el perfil 1 vCPU / 2 GB).
