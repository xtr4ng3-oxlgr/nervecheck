# Arquitectura

NERVECHECK usa una arquitectura local:

```text
GUI -> scanner -> metrics/findings -> dashboard -> reports
```

Componentes:

- `src/nervecheck.py`: aplicación principal.
- `reports/`: reportes HTML/JSON.
- `logs/`: errores locales.
- `data/`: historial local.

Dependencia principal:

- `psutil`: métricas de CPU, RAM, procesos, disco y red.
