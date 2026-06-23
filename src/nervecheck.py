
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as dt
import html
import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "NERVECHECK"
APP_VERSION = "1.0.0"
AUTHOR = "xtr4ng3"
IS_WINDOWS = os.name == "nt"

try:
    import psutil  # type: ignore
    HAS_PSUTIL = True
except Exception:
    psutil = None
    HAS_PSUTIL = False

ASCII_HEADER = r"""
███╗   ██╗███████╗██████╗ ██╗   ██╗███████╗ ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗
████╗  ██║██╔════╝██╔══██╗██║   ██║██╔════╝██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝
██╔██╗ ██║█████╗  ██████╔╝██║   ██║█████╗  ██║     ███████║█████╗  ██║     █████╔╝ 
██║╚██╗██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ 
██║ ╚████║███████╗██║  ██║ ╚████╔╝ ███████╗╚██████╗██║  ██║███████╗╚██████╗██║  ██╗
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝
                         LOCAL PC HEALTH / STABILITY / PERFORMANCE
""".strip("\n")


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.upper() == "NERVECHECK":
            return exe_dir.parent
        return exe_dir
    return Path.cwd()

BASE_DIR = app_base_dir()
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"
for d in (DATA_DIR, REPORT_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

ERROR_LOG = LOG_DIR / "errors.log"
HISTORY_FILE = DATA_DIR / "history.json"


@dataclass
class Finding:
    level: str
    category: str
    title: str
    detail: str
    recommendation: str


@dataclass
class Metric:
    name: str
    value: str
    status: str


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu: float
    memory_mb: float
    path: str


@dataclass
class StartupInfo:
    source: str
    name: str
    command: str
    score: int
    note: str


@dataclass
class EventInfo:
    source: str
    event_id: str
    level: str
    time_created: str
    message: str


@dataclass
class ScanResult:
    generated_at: str
    score: int
    verdict: str
    metrics: List[Metric]
    findings: List[Finding]
    processes: List[ProcessInfo]
    startup: List[StartupInfo]
    events: List[EventInfo]
    system: Dict[str, str]


def log_error(exc: BaseException) -> None:
    try:
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{dt.datetime.now().isoformat(timespec='seconds')}]\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def bytes_human(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def open_path(path: Path) -> None:
    try:
        if IS_WINDOWS:
            os.startfile(str(path))
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as exc:
        log_error(exc)


def verdict_from_score(score: int) -> str:
    if score >= 85:
        return "Crítico"
    if score >= 65:
        return "Alto"
    if score >= 40:
        return "Medio"
    if score >= 20:
        return "Leve"
    return "Estable"


def status_percent(value: float, warn: float, bad: float) -> str:
    if value >= bad:
        return "CRÍTICO"
    if value >= warn:
        return "ATENCIÓN"
    return "OK"


def add_finding(items: List[Finding], level: str, category: str, title: str, detail: str, recommendation: str) -> None:
    items.append(Finding(level, category, title, detail, recommendation))


def run_cmd(args: List[str], timeout: int = 15) -> str:
    try:
        flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
        cp = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=timeout, creationflags=flags)
        return (cp.stdout or "") + (cp.stderr or "")
    except Exception as exc:
        log_error(exc)
        return ""


def get_system_info() -> Dict[str, str]:
    info = {
        "tool": APP_NAME,
        "version": APP_VERSION,
        "author": AUTHOR,
        "python": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "version_os": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "psutil": "available" if HAS_PSUTIL else "missing",
    }
    if HAS_PSUTIL:
        try:
            info["boot_time"] = dt.datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds")
            uptime = time.time() - psutil.boot_time()
            info["uptime"] = human_duration(uptime)
            info["cpu_logical"] = str(psutil.cpu_count(logical=True))
            info["cpu_physical"] = str(psutil.cpu_count(logical=False))
        except Exception as exc:
            log_error(exc)
    return info


def human_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def collect_metrics() -> Tuple[List[Metric], List[Finding], int]:
    metrics: List[Metric] = []
    findings: List[Finding] = []
    score = 0

    if not HAS_PSUTIL:
        metrics.append(Metric("psutil", "No instalado", "LIMITADO"))
        add_finding(findings, "medio", "dependencias", "Diagnóstico limitado", "psutil no está instalado.", "Ejecutar build_windows\\INSTALAR_DEPENDENCIAS.bat para activar métricas completas.")
        return metrics, findings, 15

    try:
        cpu = psutil.cpu_percent(interval=0.8)
        metrics.append(Metric("CPU uso", f"{cpu:.1f}%", status_percent(cpu, 75, 90)))
        if cpu >= 90:
            add_finding(findings, "alto", "cpu", "CPU saturada", f"Uso actual de CPU: {cpu:.1f}%.", "Cerrar procesos pesados o reiniciar si la carga no baja.")
            score += 22
        elif cpu >= 75:
            add_finding(findings, "medio", "cpu", "CPU elevada", f"Uso actual de CPU: {cpu:.1f}%.", "Revisar procesos pesados.")
            score += 10
    except Exception as exc:
        log_error(exc)

    try:
        mem = psutil.virtual_memory()
        metrics.append(Metric("RAM uso", f"{mem.percent:.1f}% ({bytes_human(mem.used)} / {bytes_human(mem.total)})", status_percent(mem.percent, 78, 92)))
        if mem.percent >= 92:
            add_finding(findings, "alto", "ram", "RAM casi agotada", f"Uso de RAM: {mem.percent:.1f}%.", "Cerrar apps pesadas o ampliar memoria si se repite.")
            score += 24
        elif mem.percent >= 78:
            add_finding(findings, "medio", "ram", "RAM alta", f"Uso de RAM: {mem.percent:.1f}%.", "Revisar procesos con mayor consumo.")
            score += 12
    except Exception as exc:
        log_error(exc)

    try:
        swap = psutil.swap_memory()
        if swap.total > 0:
            metrics.append(Metric("Memoria virtual", f"{swap.percent:.1f}% ({bytes_human(swap.used)} / {bytes_human(swap.total)})", status_percent(swap.percent, 40, 70)))
            if swap.percent >= 70:
                add_finding(findings, "medio", "swap", "Memoria virtual muy usada", "El sistema está usando bastante memoria virtual.", "Puede haber falta de RAM o demasiadas apps abiertas.")
                score += 10
    except Exception as exc:
        log_error(exc)

    try:
        for part in psutil.disk_partitions(all=False):
            if not part.mountpoint:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                metrics.append(Metric(f"Disco {part.mountpoint}", f"{usage.percent:.1f}% usado ({bytes_human(usage.free)} libre)", status_percent(usage.percent, 85, 95)))
                if usage.percent >= 95:
                    add_finding(findings, "alto", "disco", f"Disco casi lleno: {part.mountpoint}", f"Uso: {usage.percent:.1f}%.", "Liberar espacio. Windows y juegos pueden fallar con poco espacio.")
                    score += 22
                elif usage.percent >= 85:
                    add_finding(findings, "medio", "disco", f"Disco con poco espacio: {part.mountpoint}", f"Uso: {usage.percent:.1f}%.", "Limpiar temporales, descargas viejas y archivos grandes.")
                    score += 10
            except Exception:
                pass
    except Exception as exc:
        log_error(exc)

    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            got = False
            for name, entries in temps.items():
                for e in entries:
                    if e.current:
                        got = True
                        st = "OK"
                        if e.current >= 90:
                            st = "CRÍTICO"
                            score += 20
                            add_finding(findings, "alto", "temperatura", f"Temperatura alta: {name}", f"{e.current:.1f}°C.", "Revisar ventilación, polvo, pasta térmica o carga excesiva.")
                        elif e.current >= 80:
                            st = "ATENCIÓN"
                            score += 8
                        metrics.append(Metric(f"Temp {e.label or name}", f"{e.current:.1f}°C", st))
            if not got:
                metrics.append(Metric("Temperaturas", "No disponibles desde Python", "INFO"))
        else:
            metrics.append(Metric("Temperaturas", "No disponibles", "INFO"))
    except Exception:
        metrics.append(Metric("Temperaturas", "No disponibles", "INFO"))

    try:
        battery = psutil.sensors_battery()
        if battery:
            state = "cargando" if battery.power_plugged else "batería"
            metrics.append(Metric("Batería", f"{battery.percent:.1f}% · {state}", "OK" if battery.percent > 25 else "ATENCIÓN"))
    except Exception:
        pass

    try:
        net = psutil.net_io_counters()
        metrics.append(Metric("Red enviada", bytes_human(net.bytes_sent), "INFO"))
        metrics.append(Metric("Red recibida", bytes_human(net.bytes_recv), "INFO"))
    except Exception:
        pass

    return metrics, findings, min(score, 100)


def collect_processes(limit: int = 15) -> List[ProcessInfo]:
    if not HAS_PSUTIL:
        return []
    results: List[ProcessInfo] = []
    try:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                p.cpu_percent(None)
            except Exception:
                pass
        time.sleep(0.4)
        for p in psutil.process_iter(["pid", "name", "memory_info", "exe"]):
            try:
                mem = p.info.get("memory_info")
                mem_mb = (mem.rss / 1024 / 1024) if mem else 0.0
                results.append(ProcessInfo(int(p.info.get("pid") or 0), p.info.get("name") or "", float(p.cpu_percent(None)), float(mem_mb), p.info.get("exe") or ""))
            except Exception:
                continue
    except Exception as exc:
        log_error(exc)
    results.sort(key=lambda x: (x.cpu, x.memory_mb), reverse=True)
    return results[:limit]


def collect_startup() -> List[StartupInfo]:
    results: List[StartupInfo] = []

    def score_command(cmd: str) -> Tuple[int, str]:
        lower = cmd.lower()
        score = 0
        notes = []
        for x in ["\\appdata\\", "\\temp\\", "\\downloads\\", "\\descargas\\", "\\public\\"]:
            if x in lower:
                score += 20
                notes.append(f"ruta sensible {x}")
                break
        for x in ["powershell", "cmd.exe", "wscript", "cscript", "mshta", ".bat", ".cmd", ".ps1", ".vbs", ".js"]:
            if x in lower:
                score += 25
                notes.append(f"comando/script {x}")
                break
        if "http://" in lower or "https://" in lower:
            score += 15
            notes.append("contiene URL")
        if "-enc" in lower or "encodedcommand" in lower:
            score += 35
            notes.append("comando codificado")
        return min(score, 100), "; ".join(notes) if notes else "inicio común"

    if IS_WINDOWS:
        folders = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        if appdata:
            folders.append(Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup")
        if programdata:
            folders.append(Path(programdata) / r"Microsoft\Windows\Start Menu\Programs\Startup")
        for folder in folders:
            if folder.exists():
                for item in folder.iterdir():
                    score, note = score_command(str(item))
                    results.append(StartupInfo(f"Startup folder: {folder}", item.name, str(item), score, note))
        try:
            import winreg
            keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
            ]
            for hive, subkey, label in keys:
                try:
                    with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                score, note = score_command(str(value))
                                results.append(StartupInfo(label, str(name), str(value), score, note))
                                i += 1
                            except OSError:
                                break
                except OSError:
                    continue
        except Exception as exc:
            log_error(exc)
    return sorted(results, key=lambda x: x.score, reverse=True)


def collect_events(limit: int = 20) -> List[EventInfo]:
    events: List[EventInfo] = []
    if not IS_WINDOWS:
        return events
    out = run_cmd(["wevtutil", "qe", "System", "/q:*[System[(Level=1 or Level=2)]]", "/c:25", "/rd:true", "/f:text"], timeout=20)
    if not out:
        return events
    for ch in out.split("\n\n"):
        if len(events) >= limit:
            break
        lines = [x.strip() for x in ch.splitlines() if x.strip()]
        if not lines:
            continue
        source = event_id = level = time_created = msg = ""
        for line in lines:
            low = line.lower()
            if low.startswith("provider name:"):
                source = line.split(":", 1)[-1].strip()
            elif low.startswith("event id:"):
                event_id = line.split(":", 1)[-1].strip()
            elif low.startswith("level:"):
                level = line.split(":", 1)[-1].strip()
            elif low.startswith("date:"):
                time_created = line.split(":", 1)[-1].strip()
            elif len(msg) < 240 and not any(low.startswith(p) for p in ["provider", "event", "version", "level", "task", "opcode", "keywords", "time", "event record", "correlation", "execution", "channel", "computer", "security"]):
                msg += line[:180] + " "
        if source or event_id:
            events.append(EventInfo(source or "System", event_id or "-", level or "-", time_created or "-", msg.strip()[:260]))
    return events


def analyze_events(events: List[EventInfo], findings: List[Finding]) -> int:
    score = 0
    if not events:
        return score
    kernel_power = sum(1 for e in events if e.event_id.strip() == "41" or "kernel-power" in e.source.lower())
    whea = sum(1 for e in events if "whea" in e.source.lower())
    disk = sum(1 for e in events if "disk" in e.source.lower() or "ntfs" in e.source.lower())
    service = sum(1 for e in events if "service control" in e.source.lower())
    if kernel_power:
        add_finding(findings, "alto", "estabilidad", "Reinicios inesperados detectados", f"Eventos Kernel-Power o equivalentes: {kernel_power}.", "Revisar fuente, temperatura, drivers, cortes de energía y estabilidad general.")
        score += 22
    if whea:
        add_finding(findings, "alto", "hardware", "Eventos WHEA detectados", f"Eventos relacionados con hardware: {whea}.", "Revisar CPU, RAM, overclock, temperaturas y fuente.")
        score += 25
    if disk:
        add_finding(findings, "alto", "disco", "Eventos de disco o sistema de archivos", f"Eventos relacionados con disco/NTFS: {disk}.", "Hacer backup y revisar salud del disco con herramientas especializadas.")
        score += 25
    if service >= 5:
        add_finding(findings, "medio", "servicios", "Múltiples errores de servicios", f"Errores de servicios detectados: {service}.", "Revisar servicios fallando y programas instalados recientemente.")
        score += 8
    return min(score, 100)


def full_scan() -> ScanResult:
    system = get_system_info()
    metrics, findings, score = collect_metrics()
    processes = collect_processes()
    startup = collect_startup()
    events = collect_events()
    score += analyze_events(events, findings)
    risky_startup = [s for s in startup if s.score >= 50]
    if risky_startup:
        add_finding(findings, "medio", "inicio", "Entradas de inicio con señales de atención", f"{len(risky_startup)} entradas de inicio tienen rutas, comandos o scripts que conviene revisar.", "Abrir la pestaña Inicio y verificar origen de cada entrada.")
        score += min(15, len(risky_startup) * 5)
    if HAS_PSUTIL and processes:
        if processes[0].cpu >= 50:
            add_finding(findings, "medio", "procesos", "Proceso con alto uso de CPU", f"{processes[0].name} usa aproximadamente {processes[0].cpu:.1f}% de CPU.", "Si no corresponde a una tarea esperada, cerrarlo o reiniciar.")
            score += 10
        if processes[0].memory_mb >= 1500:
            add_finding(findings, "medio", "procesos", "Proceso con alto uso de memoria", f"{processes[0].name} usa aproximadamente {processes[0].memory_mb:.0f} MB.", "Revisar si corresponde a navegador, juego o programa pesado.")
            score += 8
    score = min(score, 100)
    if not findings:
        add_finding(findings, "info", "general", "Sistema estable en revisión rápida", "No se detectaron señales críticas con reglas locales.", "Mantener drivers, Windows y backups al día.")
    return ScanResult(now_iso(), score, verdict_from_score(score), metrics, findings, processes, startup, events, system)


def save_history(result: ScanResult) -> None:
    try:
        history = []
        if HISTORY_FILE.exists():
            loaded = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            history = loaded if isinstance(loaded, list) else []
        history.insert(0, {"date": result.generated_at, "score": result.score, "verdict": result.verdict, "findings": len(result.findings)})
        HISTORY_FILE.write_text(json.dumps(history[:100], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def export_json(result: ScanResult, path: Path) -> None:
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")


def export_html(result: ScanResult, path: Path) -> None:
    def color_status(status: str) -> str:
        s = status.upper()
        if "CRÍTICO" in s or "ALTO" in s:
            return "#ff304f"
        if "ATENCIÓN" in s or "MEDIO" in s:
            return "#ffd166"
        if "OK" in s or "ESTABLE" in s:
            return "#5dff8b"
        return "#8ab4c8"
    score_color = "#5dff8b"
    if result.score >= 85:
        score_color = "#ff304f"
    elif result.score >= 65:
        score_color = "#ff5a36"
    elif result.score >= 40:
        score_color = "#ffd166"
    findings_rows = "".join(f"<tr><td>{html.escape(f.level)}</td><td>{html.escape(f.category)}</td><td><b>{html.escape(f.title)}</b><br>{html.escape(f.detail)}</td><td>{html.escape(f.recommendation)}</td></tr>" for f in result.findings)
    metric_rows = "".join(f"<tr><td>{html.escape(m.name)}</td><td>{html.escape(m.value)}</td><td style='color:{color_status(m.status)}'>{html.escape(m.status)}</td></tr>" for m in result.metrics)
    proc_rows = "".join(f"<tr><td>{p.pid}</td><td>{html.escape(p.name)}</td><td>{p.cpu:.1f}%</td><td>{p.memory_mb:.1f} MB</td><td><code>{html.escape(p.path)}</code></td></tr>" for p in result.processes)
    start_rows = "".join(f"<tr><td>{s.score}</td><td>{html.escape(s.source)}</td><td>{html.escape(s.name)}</td><td><code>{html.escape(s.command)}</code></td><td>{html.escape(s.note)}</td></tr>" for s in result.startup)
    event_rows = "".join(f"<tr><td>{html.escape(e.time_created)}</td><td>{html.escape(e.source)}</td><td>{html.escape(e.event_id)}</td><td>{html.escape(e.level)}</td><td>{html.escape(e.message)}</td></tr>" for e in result.events)
    system_rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>" for k, v in result.system.items())
    doc = f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><title>NERVECHECK Report</title>
<style>body{{background:#05070b;color:#e8f6ff;font-family:Consolas,Segoe UI,Arial;padding:30px}}h1,h2{{color:#ff304f}}.card{{background:#0b1018;border:1px solid #202c3f;border-radius:16px;padding:18px;margin:18px 0;box-shadow:0 0 24px rgba(255,48,79,.08)}}table{{width:100%;border-collapse:collapse;margin-top:12px}}td,th{{border-bottom:1px solid #1a2130;padding:9px;text-align:left;vertical-align:top}}th{{color:#7ef9ff}}code{{color:#d6f7ff}}.score{{font-size:56px;font-weight:900;color:{score_color}}}.small{{color:#9fb1c7;font-size:13px}}</style></head><body>
<h1>NERVECHECK</h1><p class='small'>Local PC Health / Stability / Performance · xtr4ng3 · {html.escape(result.generated_at)}</p>
<div class='card'><h2>Verdict</h2><div class='score'>{result.score}/100</div><p><b>{html.escape(result.verdict)}</b></p></div>
<div class='card'><h2>Metrics</h2><table><tr><th>Métrica</th><th>Valor</th><th>Estado</th></tr>{metric_rows}</table></div>
<div class='card'><h2>Findings</h2><table><tr><th>Nivel</th><th>Categoría</th><th>Detalle</th><th>Recomendación</th></tr>{findings_rows}</table></div>
<div class='card'><h2>Procesos pesados</h2><table><tr><th>PID</th><th>Nombre</th><th>CPU</th><th>RAM</th><th>Ruta</th></tr>{proc_rows}</table></div>
<div class='card'><h2>Inicio de Windows</h2><table><tr><th>Score</th><th>Fuente</th><th>Nombre</th><th>Comando</th><th>Nota</th></tr>{start_rows}</table></div>
<div class='card'><h2>Eventos críticos recientes</h2><table><tr><th>Fecha</th><th>Fuente</th><th>ID</th><th>Nivel</th><th>Mensaje</th></tr>{event_rows if event_rows else '<tr><td colspan="5">No se cargaron eventos o no hay datos disponibles.</td></tr>'}</table></div>
<div class='card'><h2>Sistema</h2><table><tr><th>Campo</th><th>Valor</th></tr>{system_rows}</table></div>
<p class='small'>NERVECHECK no modifica el sistema. Es diagnóstico local.</p></body></html>"""
    path.write_text(doc, encoding="utf-8")


class NerveCheckApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NERVECHECK // xtr4ng3")
        self.root.geometry("1380x900")
        self.root.minsize(1180, 760)
        self.result: Optional[ScanResult] = None
        self.queue: queue.Queue = queue.Queue()
        self.live = False
        self.setup_style()
        self.build_ui()
        self.refresh_live_once()
        self.log("NERVECHECK listo. Ejecutá un escaneo rápido o activá modo live.")

    def setup_style(self):
        self.root.configure(bg="#05070b")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background="#05070b", foreground="#edf7ff", fieldbackground="#0b1018")
        style.configure("TFrame", background="#05070b")
        style.configure("Panel.TFrame", background="#0b1018")
        style.configure("TLabel", background="#05070b", foreground="#edf7ff")
        style.configure("Panel.TLabel", background="#0b1018", foreground="#edf7ff")
        style.configure("Header.TLabel", background="#05070b", foreground="#ff304f", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background="#05070b", foreground="#9fb1c7", font=("Segoe UI", 9))
        style.configure("Score.TLabel", background="#0b1018", foreground="#ffffff", font=("Segoe UI", 26, "bold"))
        style.configure("Accent.TButton", background="#5b0f1a", foreground="#ffffff", padding=8)
        style.map("Accent.TButton", background=[("active", "#8a1328")])
        style.configure("TButton", background="#121927", foreground="#edf7ff", padding=7)
        style.map("TButton", background=[("active", "#1a2436")])
        style.configure("Treeview", background="#090d14", foreground="#edf7ff", fieldbackground="#090d14", rowheight=27)
        style.configure("Treeview.Heading", background="#11192a", foreground="#7ef9ff")
        style.configure("TNotebook.Tab", background="#121927", foreground="#edf7ff", padding=(12, 7))
        style.map("TNotebook.Tab", background=[("selected", "#5b0f1a")], foreground=[("selected", "#ffffff")])

    def build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=14, pady=(10, 6))
        banner_frame = ttk.Frame(top, style="Panel.TFrame")
        banner_frame.pack(fill=tk.X)
        banner = tk.Text(banner_frame, height=7, bg="#06080d", fg="#ff304f", relief="flat", font=("Consolas", 9, "bold"))
        banner.pack(fill=tk.X)
        banner.insert("1.0", ASCII_HEADER)
        banner.config(state="disabled")
        title = ttk.Frame(top)
        title.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(title, text="NERVECHECK", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(title, text="  Local PC Health / Stability / Performance", style="Sub.TLabel").pack(side=tk.LEFT, padx=10)
        buttons = ttk.Frame(self.root)
        buttons.pack(fill=tk.X, padx=14, pady=(2, 8))
        ttk.Button(buttons, text="ESCANEO RÁPIDO", style="Accent.TButton", command=self.start_scan).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="LIVE ON/OFF", command=self.toggle_live).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Exportar HTML", command=self.export_html_ui).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Exportar JSON", command=self.export_json_ui).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Abrir reportes", command=lambda: open_path(REPORT_DIR)).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Instalar deps", command=self.show_install_help).pack(side=tk.LEFT, padx=4)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)
        self.tab_dashboard = ttk.Frame(self.notebook); self.tab_metrics = ttk.Frame(self.notebook); self.tab_processes = ttk.Frame(self.notebook); self.tab_startup = ttk.Frame(self.notebook); self.tab_events = ttk.Frame(self.notebook); self.tab_system = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text="Dashboard"); self.notebook.add(self.tab_metrics, text="Métricas"); self.notebook.add(self.tab_processes, text="Procesos"); self.notebook.add(self.tab_startup, text="Inicio"); self.notebook.add(self.tab_events, text="Eventos"); self.notebook.add(self.tab_system, text="Sistema")
        self.build_dashboard(); self.build_metrics_tab(); self.build_processes_tab(); self.build_startup_tab(); self.build_events_tab(); self.build_system_tab()
        bottom = ttk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=14, pady=(0, 10))
        ttk.Label(bottom, text="Registro", style="Sub.TLabel").pack(anchor="w")
        self.log_box = tk.Text(bottom, height=5, bg="#06080d", fg="#d9f6ff", relief="flat", insertbackground="#ffffff")
        self.log_box.pack(fill=tk.X, pady=(4, 0))
        self.root.after(200, self.process_queue)

    def build_dashboard(self):
        frame = ttk.Frame(self.tab_dashboard); frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        cards = ttk.Frame(frame); cards.pack(fill=tk.X)
        self.score_var = tk.StringVar(value="--/100"); self.verdict_var = tk.StringVar(value="Sin escaneo"); self.cpu_var = tk.StringVar(value="CPU --"); self.ram_var = tk.StringVar(value="RAM --"); self.disk_var = tk.StringVar(value="DISK --"); self.dep_var = tk.StringVar(value="psutil: " + ("OK" if HAS_PSUTIL else "FALTA"))
        for title, var in [("SCORE", self.score_var),("VEREDICTO", self.verdict_var),("CPU", self.cpu_var),("RAM", self.ram_var),("DISCO", self.disk_var),("MODO", self.dep_var)]:
            card = ttk.Frame(cards, style="Panel.TFrame"); card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            ttk.Label(card, text=title, style="Panel.TLabel").pack(anchor="w", padx=12, pady=(10, 0))
            ttk.Label(card, textvariable=var, style="Score.TLabel").pack(anchor="w", padx=12, pady=(0, 12))
        ttk.Label(frame, text="Hallazgos", style="Sub.TLabel").pack(anchor="w", pady=(12, 4))
        self.findings_tree = ttk.Treeview(frame, columns=("level","cat","title","rec"), show="headings")
        for col, title, width in [("level","Nivel",90),("cat","Categoría",130),("title","Hallazgo",440),("rec","Recomendación",620)]:
            self.findings_tree.heading(col, text=title); self.findings_tree.column(col, width=width)
        self.findings_tree.pack(fill=tk.BOTH, expand=True)

    def make_tree(self, parent, cols):
        frame = ttk.Frame(parent); frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="headings")
        for col, title, width in cols:
            tree.heading(col, text=title); tree.column(col, width=width)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def build_metrics_tab(self):
        self.metrics_tree = self.make_tree(self.tab_metrics, [("name","Métrica",260),("value","Valor",520),("status","Estado",160)])
    def build_processes_tab(self):
        self.proc_tree = self.make_tree(self.tab_processes, [("pid","PID",80),("name","Proceso",240),("cpu","CPU",100),("ram","RAM",120),("path","Ruta",720)])
    def build_startup_tab(self):
        self.start_tree = self.make_tree(self.tab_startup, [("score","Score",80),("source","Fuente",220),("name","Nombre",220),("cmd","Comando",620),("note","Nota",240)])
    def build_events_tab(self):
        self.event_tree = self.make_tree(self.tab_events, [("time","Fecha",170),("source","Fuente",220),("id","ID",80),("level","Nivel",100),("msg","Mensaje",700)])
    def build_system_tab(self):
        self.system_tree = self.make_tree(self.tab_system, [("field","Campo",260),("value","Valor",900)])

    def start_scan(self):
        self.log("Escaneo iniciado...")
        threading.Thread(target=self.scan_worker, daemon=True).start()
    def scan_worker(self):
        try:
            result = full_scan(); save_history(result); self.queue.put(("scan_result", result))
        except Exception as exc:
            log_error(exc); self.queue.put(("error", str(exc)))
    def process_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "scan_result":
                    self.apply_result(payload); self.log(f"Escaneo completado: {payload.verdict} · {payload.score}/100")
                elif kind == "error":
                    self.log(f"Error: {payload}")
        except queue.Empty:
            pass
        self.root.after(200, self.process_queue)

    def apply_result(self, result: ScanResult):
        self.result = result
        self.score_var.set(f"{result.score}/100"); self.verdict_var.set(result.verdict.upper())
        cpu = next((m for m in result.metrics if m.name == "CPU uso"), None)
        ram = next((m for m in result.metrics if m.name == "RAM uso"), None)
        disk = next((m for m in result.metrics if m.name.startswith("Disco")), None)
        self.cpu_var.set(cpu.value if cpu else "--"); self.ram_var.set(ram.value.split(" ")[0] if ram else "--"); self.disk_var.set(disk.value.split(" ")[0] if disk else "--"); self.dep_var.set("LIVE" if self.live else ("FULL" if HAS_PSUTIL else "LIMITADO"))
        self.findings_tree.delete(*self.findings_tree.get_children())
        for f in result.findings: self.findings_tree.insert("", tk.END, values=(f.level, f.category, f.title, f.recommendation))
        self.metrics_tree.delete(*self.metrics_tree.get_children())
        for m in result.metrics: self.metrics_tree.insert("", tk.END, values=(m.name, m.value, m.status))
        self.proc_tree.delete(*self.proc_tree.get_children())
        for p in result.processes: self.proc_tree.insert("", tk.END, values=(p.pid, p.name, f"{p.cpu:.1f}%", f"{p.memory_mb:.1f} MB", p.path))
        self.start_tree.delete(*self.start_tree.get_children())
        for s in result.startup: self.start_tree.insert("", tk.END, values=(s.score, s.source, s.name, s.command, s.note))
        self.event_tree.delete(*self.event_tree.get_children())
        for e in result.events: self.event_tree.insert("", tk.END, values=(e.time_created, e.source, e.event_id, e.level, e.message))
        self.system_tree.delete(*self.system_tree.get_children())
        for k, v in result.system.items(): self.system_tree.insert("", tk.END, values=(k, v))

    def refresh_live_once(self):
        if HAS_PSUTIL:
            try:
                self.cpu_var.set(f"{psutil.cpu_percent(interval=None):.1f}%")
                self.ram_var.set(f"{psutil.virtual_memory().percent:.1f}%")
            except Exception: pass
        if self.live:
            self.start_scan()
        self.root.after(5000, self.refresh_live_once)
    def toggle_live(self):
        self.live = not self.live; self.dep_var.set("LIVE" if self.live else ("FULL" if HAS_PSUTIL else "LIMITADO")); self.log("Modo live activado." if self.live else "Modo live desactivado.")
    def export_html_ui(self):
        if not self.result: messagebox.showwarning(APP_NAME, "Primero ejecutá un escaneo."); return
        path = REPORT_DIR / f"nervecheck_report_{now_stamp()}.html"; export_html(self.result, path); self.log(f"HTML exportado: {path}"); open_path(path)
    def export_json_ui(self):
        if not self.result: messagebox.showwarning(APP_NAME, "Primero ejecutá un escaneo."); return
        path = REPORT_DIR / f"nervecheck_report_{now_stamp()}.json"; export_json(self.result, path); self.log(f"JSON exportado: {path}"); open_path(path.parent)
    def show_install_help(self):
        messagebox.showinfo(APP_NAME, "Para activar métricas completas instalá psutil.\n\nForma fácil:\nbuild_windows\\INSTALAR_DEPENDENCIAS.bat\n\nManual:\npy -3 -m pip install psutil")
    def log(self, text: str):
        line = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {text}"; self.log_box.insert(tk.END, line + "\n"); self.log_box.see(tk.END)
    def run(self): self.root.mainloop()


def main():
    try:
        NerveCheckApp().run()
    except Exception as exc:
        log_error(exc)
        try: messagebox.showerror(APP_NAME, f"Error crítico:\n{exc}\n\nRevisar logs/errors.log")
        except Exception: print(exc)

if __name__ == "__main__":
    main()
