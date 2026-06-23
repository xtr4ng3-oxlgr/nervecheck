# NERVECHECK

<img width="1448" height="1086" alt="nervech" src="https://github.com/user-attachments/assets/24c43b84-55d6-4c16-a4ef-c10e41d65cbc" />

**NERVECHECK** es una herramienta local de diagnóstico de PC para revisar rendimiento, estabilidad, memoria, disco, procesos, inicio de Windows, eventos críticos y estado general del sistema.

Creado por **xtr4ng3**.

## Propósito

Una PC puede sentirse lenta, inestable o extraña por muchas razones: falta de RAM, disco lleno, procesos pesados, reinicios inesperados, errores de hardware, eventos críticos, programas cargando al inicio o demasiada carga al mismo tiempo.

NERVECHECK reúne esas señales en una interfaz visual y en reportes claros para entender qué está pasando sin abrir muchas herramientas distintas.

No modifica el sistema.  
No borra archivos.  
No desactiva programas.  
Solo revisa, organiza y reporta.

## Funciones

- dashboard visual,
- modo live,
- uso de CPU,
- uso de RAM,
- discos y espacio libre,
- memoria virtual,
- batería si está disponible,
- red enviada y recibida,
- procesos pesados,
- entradas de inicio de Windows,
- eventos críticos recientes del sistema,
- detección de reinicios inesperados,
- detección de eventos WHEA,
- detección de errores de disco o NTFS,
- reporte HTML,
- reporte JSON,
- historial local.

## Dependencias

NERVECHECK usa `psutil` para métricas completas.

Puede abrir sin `psutil`, pero el diagnóstico será limitado.

Instalación rápida en Windows:

```bat
build_windows\INSTALAR_DEPENDENCIAS.bat
```

Instalación manual:

```bash
pip install psutil
```

## Ejecutar

```bash
python src/nervecheck.py
```

En Windows:

```bat
run_nervecheck.bat
```

## Compilar portable

En Windows:

```bat
build_windows\1_COMPILAR_EXE_PORTABLE.bat
```

La compilación genera:

```text
CLIENTE_PORTABLE/
```


# Licencia

<img width="300" height="159" alt="giphy (25)" src="https://github.com/user-attachments/assets/021720ff-3aec-4916-9a93-25d47afd7d97" />

**xtr4ng3**

MIT.
