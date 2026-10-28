"""
Reset AnyDesk v5
Clicou — funciona. Auto-setup completo.
Desenvolvido por Estevão Santos — TSCBr (Technology Solution Company) — 2026
"""

import ctypes
import sys
import os
import subprocess
import threading
import time
import json
import shutil
import logging
import urllib.request
import winreg
from pathlib import Path

# ── Admin imediato (antes de qualquer import de UI) ───────────────────────────
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1)
    sys.exit()

if not is_admin():
    elevate()

# ── Paths base ────────────────────────────────────────────────────────────────
APP_DIR       = Path("C:/Reset Anydesk")
LOG_PATH      = APP_DIR / "reset_log.txt"
HIST_PATH     = APP_DIR / "historico.json"
SETUP_FLAG    = APP_DIR / ".setup_ok"        # existe → setup já foi feito
ICON_PATH     = APP_DIR / "icone.ico"
ANYDESK_INST  = APP_DIR / "AnyDesk_9.6.11.exe"

APP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ── Constantes ────────────────────────────────────────────────────────────────
ANYDESK_VERSION   = "9.6.11"
ANYDESK_URL       = "https://download.anydesk.com/AnyDesk.exe"
PYTHON_URL_64     = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
PYTHON_URL_32     = "https://www.python.org/ftp/python/3.12.4/python-3.12.4.exe"

ANYDESK_EXE_64    = Path(os.environ.get("ProgramFiles",       "C:/Program Files"))       / "AnyDesk/AnyDesk.exe"
ANYDESK_EXE_86    = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "AnyDesk/AnyDesk.exe"
ANYDESK_DATA      = Path(os.environ.get("ALLUSERSPROFILE",   "C:/ProgramData"))          / "AnyDesk"
ANYDESK_USER      = Path(os.environ.get("APPDATA",           ""))                        / "AnyDesk"
TEMP_DIR          = Path(os.environ.get("TEMP",              "C:/Temp"))

COOLDOWN_SECS     = 30
FORCE_LIMIT       = 1

NO_WIN = subprocess.CREATE_NO_WINDOW

# ── Cores ─────────────────────────────────────────────────────────────────────
C_BG      = "#111318"
C_CARD    = "#1a1d27"
C_CARD2   = "#13151e"
C_ACCENT  = "#10bfe1"
C_ACCENT2 = "#0d9cb8"
C_TEXT    = "#e2e8f0"
C_MUTED   = "#4a5568"
C_BORDER  = "#1e2130"
C_GREEN   = "#22c55e"
C_YELLOW  = "#f59e0b"
C_RED     = "#ef4444"

APP_VERSION = "v26.4.10"
FOOTER = f"Desenvolvido por Estevão Miguel  —  Todos os Direitos Reservados  —  {APP_VERSION}  —  2026"


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE SISTEMA
# ═══════════════════════════════════════════════════════════════════════════════

def run(cmd, timeout=30):
    try:
        return subprocess.run(
            cmd, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WIN,
            timeout=timeout
        ).returncode
    except Exception:
        return -1

def anydesk_exe():
    for p in (ANYDESK_EXE_64, ANYDESK_EXE_86):
        if p.exists():
            return p
    return None

def anydesk_installed_version():
    """Lê versão do AnyDesk via registro do Windows."""
    keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in keys:
            try:
                with winreg.OpenKey(hive, key_path) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            sub = winreg.OpenKey(k, winreg.EnumKey(k, i))
                            name = winreg.QueryValueEx(sub, "DisplayName")[0]
                            if "anydesk" in name.lower():
                                try:
                                    return winreg.QueryValueEx(sub, "DisplayVersion")[0]
                                except Exception:
                                    return "unknown"
                        except Exception:
                            continue
            except Exception:
                continue
    return None

def service_running():
    try:
        out = subprocess.check_output(
            ["sc", "query", "AnyDesk"], text=True,
            timeout=5, stderr=subprocess.DEVNULL,
            creationflags=NO_WIN
        )
        return "RUNNING" in out
    except Exception:
        return False

def anydesk_process_running():
    """Verifica se AnyDesk.exe está rodando via ctypes."""
    import ctypes.wintypes
    kernel = ctypes.windll.kernel32
    psapi  = ctypes.windll.psapi
    arr    = (ctypes.wintypes.DWORD * 1024)()
    cb     = ctypes.wintypes.DWORD()
    psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(cb))
    count = cb.value // ctypes.sizeof(ctypes.wintypes.DWORD)
    for i in range(count):
        pid = arr[i]
        if not pid:
            continue
        h = kernel.OpenProcess(0x0410, False, pid)
        if not h:
            continue
        buf = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(h, None, buf, 260)
        kernel.CloseHandle(h)
        if buf.value.lower() == "anydesk.exe":
            return True
    return False

def stop_service(log_fn=None):
    if log_fn: log_fn("Parando serviço AnyDesk...")
    run(["sc", "stop", "AnyDesk"])
    for _ in range(15):
        if not service_running():
            break
        time.sleep(1)
    run(["taskkill", "/f", "/im", "AnyDesk.exe"])

def start_anydesk(log_fn=None):
    if log_fn: log_fn("Iniciando AnyDesk...")
    run(["sc", "start", "AnyDesk"])
    for _ in range(15):
        if service_running():
            break
        time.sleep(1)
    exe = anydesk_exe()
    if exe:
        subprocess.Popen([str(exe)], creationflags=NO_WIN)

def get_new_id():
    conf = ANYDESK_DATA / "system.conf"
    for _ in range(60):
        if conf.exists():
            try:
                for line in conf.read_text(errors="ignore").splitlines():
                    if line.startswith("ad.anynet.id="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass
        time.sleep(1)
    return None

def is_64bit():
    return sys.maxsize > 2**32

def load_history():
    try:
        if HIST_PATH.exists():
            d = json.loads(HIST_PATH.read_text(encoding="utf-8"))
            return int(d.get("resets", 0)), int(d.get("forced", 0))
    except Exception:
        pass
    return 0, 0

def save_history(resets, forced):
    try:
        HIST_PATH.write_text(
            json.dumps({"resets": resets, "forced": forced}),
            encoding="utf-8"
        )
    except Exception:
        pass

def create_shortcut():
    try:
        desktop  = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        shortcut = desktop / "Reset AnyDesk.lnk"
        if shortcut.exists():
            return
        exe = str(sys.executable if getattr(sys, "frozen", False) else Path(__file__).resolve())
        icon = str(ICON_PATH) if ICON_PATH.exists() else exe
        vbs  = TEMP_DIR / "ra_shortcut.vbs"
        vbs.write_text(
            f'Set oWS = WScript.CreateObject("WScript.Shell")\n'
            f'Set oLink = oWS.CreateShortcut("{shortcut}")\n'
            f'oLink.TargetPath = "{exe}"\n'
            f'oLink.WorkingDirectory = "{APP_DIR}"\n'
            f'oLink.IconLocation = "{icon}"\n'
            f'oLink.Description = "Reset AnyDesk"\n'
            f'oLink.Save\n',
            encoding="utf-8"
        )
        subprocess.run(["cscript", "//nologo", str(vbs)],
                       timeout=10, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=NO_WIN)
        vbs.unlink(missing_ok=True)
    except Exception as e:
        logging.warning(f"Atalho: {e}")

def copy_icon_to_appdir():
    """Copia o ícone para C:/Reset Anydesk se existir junto ao .exe."""
    try:
        src = Path(__file__).parent / "icone.ico"
        if src.exists() and not ICON_PATH.exists():
            shutil.copy2(src, ICON_PATH)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def download_file(url, dest, progress_fn=None):
    """Baixa arquivo com progresso."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    data = r.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress_fn and total:
                        progress_fn(downloaded / total)
        return True
    except Exception as e:
        logging.error(f"Download falhou: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# JANELA DE SETUP (primeira execução)
# ═══════════════════════════════════════════════════════════════════════════════

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SetupWindow(ctk.CTkToplevel):
    """Tela de configuração inicial — baixa Python e AnyDesk automaticamente."""

    def __init__(self, master, on_complete):
        super().__init__(master)
        self._on_complete = on_complete

        self.title("Reset AnyDesk — Configuração inicial")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 480, 380
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()

        try:
            if ICON_PATH.exists():
                self.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

        self._build()
        threading.Thread(target=self._run_setup, daemon=True).start()

    def _build(self):
        # Logo / título
        hdr = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="Reset AnyDesk",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C_ACCENT).place(relx=0.5, rely=0.38, anchor="center")
        ctk.CTkLabel(hdr, text="Configurando seu ambiente, aguarde...",
                     font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).place(relx=0.5, rely=0.72, anchor="center")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=20)

        # Etapas
        self._steps = {}
        steps_data = [
            ("folder",  "Criando pasta C:\\Reset Anydesk"),
            ("python",  "Verificando Python"),
            ("anydesk", "Verificando AnyDesk 9.6.11"),
            ("shortcut","Criando atalho na área de trabalho"),
            ("done",    "Tudo pronto!"),
        ]
        for key, label in steps_data:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=4)

            canvas = ctk.CTkCanvas(row, width=16, height=16,
                                   bg=C_BG, highlightthickness=0)
            canvas.pack(side="left", padx=(0, 10))
            canvas.create_oval(2, 2, 14, 14, fill=C_MUTED, outline="", tags="dot")

            lbl = ctk.CTkLabel(row, text=label,
                               font=ctk.CTkFont(size=12),
                               text_color=C_MUTED,
                               anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            self._steps[key] = (canvas, lbl)

        # Barra de progresso geral
        ctk.CTkLabel(body, text="", height=10).pack()
        self.prog_label = ctk.CTkLabel(body, text="Iniciando...",
                                        font=ctk.CTkFont(size=11),
                                        text_color=C_MUTED)
        self.prog_label.pack(anchor="w")

        self.prog_bar = ctk.CTkProgressBar(body, progress_color=C_ACCENT,
                                            fg_color=C_CARD2, height=8,
                                            corner_radius=99)
        self.prog_bar.pack(fill="x", pady=(4, 0))
        self.prog_bar.set(0)

        # Rodapé
        ctk.CTkLabel(self, text=FOOTER,
                     font=ctk.CTkFont(size=9),
                     text_color=C_MUTED).pack(pady=(0, 8))

    def _set_step(self, key, state):
        """state: 'pending' | 'running' | 'ok' | 'skip'"""
        colors = {"pending": C_MUTED, "running": C_YELLOW,
                  "ok": C_GREEN, "skip": C_MUTED}
        icons  = {"pending": C_MUTED, "running": C_YELLOW,
                  "ok": C_GREEN, "skip": C_MUTED}
        text_c = {"pending": C_MUTED, "running": C_TEXT,
                  "ok": C_TEXT, "skip": C_MUTED}
        canvas, lbl = self._steps[key]
        fill = colors[state]
        self.after(0, canvas.itemconfig, "dot", {"fill": fill})
        self.after(0, lbl.configure, {"text_color": text_c[state]})

    def _prog(self, pct, msg=""):
        self.after(0, self.prog_bar.set, pct)
        if msg:
            self.after(0, self.prog_label.configure, {"text": msg})

    def _run_setup(self):
        try:
            # ── 1. Pasta ──────────────────────────────────────────────────────
            self._set_step("folder", "running")
            self._prog(0.05, "Criando pasta C:\\Reset Anydesk...")
            APP_DIR.mkdir(parents=True, exist_ok=True)
            copy_icon_to_appdir()
            self._set_step("folder", "ok")
            self._prog(0.15)
            time.sleep(0.3)

            # ── 2. Python ─────────────────────────────────────────────────────
            self._set_step("python", "running")
            self._prog(0.15, "Verificando Python...")

            python_ok = self._check_python()
            if python_ok:
                self._set_step("python", "skip")
                self._prog(0.35, "Python já instalado. Pulando...")
                time.sleep(0.4)
            else:
                self._prog(0.20, "Baixando Python 3.12.4...")
                url  = PYTHON_URL_64 if is_64bit() else PYTHON_URL_32
                dest = APP_DIR / "python_setup.exe"

                def py_prog(p):
                    self._prog(0.20 + p * 0.20,
                               f"Baixando Python... {int(p*100)}%")

                ok = download_file(url, dest, py_prog)
                if ok:
                    self._prog(0.40, "Instalando Python...")
                    subprocess.run(
                        [str(dest), "/quiet", "InstallAllUsers=0",
                         "PrependPath=1", "Include_pip=1"],
                        timeout=180, creationflags=NO_WIN
                    )
                    dest.unlink(missing_ok=True)
                    self._set_step("python", "ok")
                else:
                    self._set_step("python", "skip")
                self._prog(0.42)

            # ── 3. AnyDesk ────────────────────────────────────────────────────
            self._set_step("anydesk", "running")
            self._prog(0.42, "Verificando AnyDesk...")

            installed_ver = anydesk_installed_version()
            need_anydesk  = (installed_ver != ANYDESK_VERSION)

            if not need_anydesk:
                self._set_step("anydesk", "skip")
                self._prog(0.75, f"AnyDesk {ANYDESK_VERSION} já instalado. Pulando...")
                time.sleep(0.4)
            else:
                action = "Atualizando" if installed_ver else "Instalando"
                self._prog(0.45, f"{action} AnyDesk {ANYDESK_VERSION}...")

                # Para qualquer instância antes de instalar
                run(["sc", "stop", "AnyDesk"])
                run(["taskkill", "/f", "/im", "AnyDesk.exe"])
                time.sleep(1)

                # Usa o instalador local se existir, senão baixa
                if ANYDESK_INST.exists():
                    installer = ANYDESK_INST
                    self._prog(0.55, "Instalador local encontrado...")
                else:
                    self._prog(0.48, "Baixando AnyDesk 9.6.11...")
                    installer = APP_DIR / "AnyDesk_setup.exe"

                    def ad_prog(p):
                        self._prog(0.48 + p * 0.20,
                                   f"Baixando AnyDesk... {int(p*100)}%")

                    ok = download_file(ANYDESK_URL, installer, ad_prog)
                    if not ok:
                        self._set_step("anydesk", "skip")
                        self._prog(0.70, "Download do AnyDesk falhou.")
                        installer = None

                if installer and installer.exists():
                    self._prog(0.70, f"{action} AnyDesk...")
                    subprocess.run(
                        [str(installer), "--install", "--silent",
                         "--create-shortcuts", "--create-desktop-icon",
                         "--start-with-win"],
                        timeout=120, creationflags=NO_WIN
                    )
                    if not ANYDESK_INST.exists() or installer != ANYDESK_INST:
                        installer.unlink(missing_ok=True)
                    time.sleep(3)
                    self._set_step("anydesk", "ok")
                self._prog(0.75)

            # ── 4. Atalho ─────────────────────────────────────────────────────
            self._set_step("shortcut", "running")
            self._prog(0.82, "Criando atalho na área de trabalho...")
            create_shortcut()
            self._set_step("shortcut", "ok")
            self._prog(0.92)
            time.sleep(0.3)

            # ── 5. Finaliza ───────────────────────────────────────────────────
            SETUP_FLAG.write_text("ok", encoding="utf-8")
            self._set_step("done", "ok")
            self._prog(1.0, "Configuração concluída!")
            time.sleep(0.8)

            self.after(0, self._complete)

        except Exception as e:
            logging.exception("Erro no setup")
            self._prog(1.0, f"Erro: {e}")

    def _check_python(self):
        try:
            r = subprocess.run(
                ["python", "--version"],
                capture_output=True, text=True,
                creationflags=NO_WIN, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False

    def _complete(self):
        self.grab_release()
        self.destroy()
        self._on_complete()


# ═══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL (minimalista)
# ═══════════════════════════════════════════════════════════════════════════════

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._reset_count, self._force_count = load_history()
        self._force_session = 0
        self._busy          = False
        self._last_reset_ts = 0.0
        self._cooldown_secs = 0
        self._cooldown_th   = None
        self._log_open      = False
        self._log_height    = 0
        self._log_target    = 160
        self._log_anim_id   = None

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(440, int(sw * 0.9))
        h  = min(560, int(sh * 0.9))
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(360, 440)
        self.resizable(True, True)
        self.title("Reset AnyDesk")
        self.configure(fg_color=C_BG)

        try:
            if ICON_PATH.exists():
                self.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

        self._build_ui()
        threading.Thread(target=self._initial_check, daemon=True).start()
        self._timer_tick()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        _h = self  # host

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(_h, fg_color=C_CARD, corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="Reset AnyDesk",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=C_ACCENT).place(relx=0.5, rely=0.5, anchor="center")

        # ── Timer card ────────────────────────────────────────────────────────
        tc = ctk.CTkFrame(_h, fg_color=C_CARD, corner_radius=10,
                          border_width=1, border_color=C_BORDER)
        tc.pack(fill="x", padx=20, pady=(16, 0))

        timer_inner = ctk.CTkFrame(tc, fg_color="transparent")
        timer_inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(timer_inner, text="Próximo reset disponível em",
                     font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(anchor="w")

        self.lbl_timer = ctk.CTkLabel(timer_inner, text="Pronto",
                                       font=ctk.CTkFont(size=28, weight="bold"),
                                       text_color=C_GREEN)
        self.lbl_timer.pack(anchor="w")

        self.timer_bar = ctk.CTkProgressBar(tc, progress_color=C_ACCENT,
                                             fg_color=C_CARD2, height=5,
                                             corner_radius=0)
        self.timer_bar.pack(fill="x", padx=0, pady=(0, 0))
        self.timer_bar.set(0)

        # ── Contadores ────────────────────────────────────────────────────────
        cc = ctk.CTkFrame(_h, fg_color="transparent")
        cc.pack(fill="x", padx=20, pady=(10, 0))
        cc.grid_columnconfigure((0, 1), weight=1)

        self._lbl_resets = self._counter(cc, "Resets", str(self._reset_count), 0)
        self._lbl_forced = self._counter(cc, "Forçados", str(self._force_count), 1)

        # ── Botões ────────────────────────────────────────────────────────────
        bf = ctk.CTkFrame(_h, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(12, 0))
        bf.grid_columnconfigure((0, 1), weight=1)

        self.btn_reset = ctk.CTkButton(
            bf, text="↺  Resetar",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C_ACCENT, hover_color=C_ACCENT2,
            text_color="#0f172a",
            corner_radius=10, height=44,
            command=lambda: self._on_reset(forced=False))
        self.btn_reset.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_force = ctk.CTkButton(
            bf, text="⚡  Forçar",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C_CARD, hover_color="#1e2436",
            text_color=C_ACCENT,
            border_width=1, border_color=C_ACCENT,
            corner_radius=10, height=44,
            command=lambda: self._on_reset(forced=True))
        self.btn_force.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # ── Progresso + Spinner ───────────────────────────────────────────────
        pf = ctk.CTkFrame(_h, fg_color=C_CARD, corner_radius=10,
                          border_width=1, border_color=C_BORDER)
        pf.pack(fill="x", padx=20, pady=(12, 0))

        pf_inner = ctk.CTkFrame(pf, fg_color="transparent")
        pf_inner.pack(fill="x", padx=14, pady=(10, 4))

        self._spinner_canvas = ctk.CTkCanvas(
            pf_inner, width=22, height=22,
            bg=C_CARD, highlightthickness=0)
        self._spinner_canvas.pack(side="left", padx=(0, 8))
        self._spinner_angle  = 0
        self._spinner_active = False
        self._draw_spinner(idle=True)

        self.lbl_step = ctk.CTkLabel(pf_inner, text="Pronto para resetar",
                                      font=ctk.CTkFont(size=11),
                                      text_color=C_MUTED,
                                      anchor="w")
        self.lbl_step.pack(side="left", fill="x", expand=True)

        self.progressbar = ctk.CTkProgressBar(pf, progress_color=C_ACCENT,
                                               fg_color=C_CARD2, height=5,
                                               corner_radius=99)
        self.progressbar.pack(fill="x", padx=14, pady=(0, 12))
        self.progressbar.set(0)

        # ── Log colapsável ────────────────────────────────────────────────────
        log_hdr = ctk.CTkFrame(_h, fg_color=C_CARD, corner_radius=10,
                                border_width=1, border_color=C_BORDER,
                                cursor="hand2")
        log_hdr.pack(fill="x", padx=20, pady=(10, 0))

        self._log_arrow = ctk.CTkLabel(log_hdr, text="▶",
                                        font=ctk.CTkFont(size=10),
                                        text_color=C_ACCENT)
        self._log_arrow.pack(side="left", padx=(14, 6), pady=10)
        ctk.CTkLabel(log_hdr, text="LOG",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C_ACCENT).pack(side="left", pady=10)
        self._log_hint = ctk.CTkLabel(log_hdr, text="clique para expandir",
                                       font=ctk.CTkFont(size=9),
                                       text_color=C_MUTED)
        self._log_hint.pack(side="right", padx=14, pady=10)

        for w in (log_hdr, self._log_arrow, self._log_hint):
            w.bind("<Button-1>", lambda e: self._toggle_log())

        self._log_container = ctk.CTkFrame(_h, fg_color="transparent")
        self._log_container.pack(fill="x", padx=20, pady=(2, 0))

        self.log_box = ctk.CTkTextbox(
            self._log_container,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=C_CARD2, text_color=C_ACCENT,
            corner_radius=10, border_width=1, border_color=C_BORDER,
            height=self._log_target, activate_scrollbars=True,
            wrap="word", state="disabled")

        # ── Rodapé ────────────────────────────────────────────────────────────
        ctk.CTkLabel(_h, text=FOOTER,
                     font=ctk.CTkFont(size=9),
                     text_color="#3a4060",
                     wraplength=420).pack(pady=(8, 6))

    # ── Spinner ───────────────────────────────────────────────────────────────

    def _draw_spinner(self, idle=False):
        c = self._spinner_canvas
        c.delete("all")
        cx, cy, r = 11, 11, 8
        if idle:
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          outline=C_MUTED, width=2)
            return
        import math
        # Arco girando
        for i in range(8):
            angle = self._spinner_angle + i * 45
            rad   = math.radians(angle)
            x1    = cx + (r-1) * math.cos(rad)
            y1    = cy + (r-1) * math.sin(rad)
            alpha = int(40 + i * 27)
            # Simula opacidade com cor interpolada
            brightness = int(16 + (alpha / 255) * (0xbf - 0x10))
            color = f"#10{brightness:02x}e1"
            c.create_oval(x1-2, y1-2, x1+2, y1+2,
                          fill=color, outline="")

    def _spinner_tick(self):
        if not self._spinner_active:
            return
        self._spinner_angle = (self._spinner_angle + 15) % 360
        self._draw_spinner()
        self.after(40, self._spinner_tick)

    def _start_spinner(self):
        self._spinner_active = True
        self._spinner_tick()

    def _stop_spinner(self, idle=False):
        self._spinner_active = False
        self._draw_spinner(idle=idle)

    def _counter(self, parent, label, value, col):
        f = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=8,
                         border_width=1, border_color=C_BORDER)
        f.grid(row=0, column=col,
               padx=(0, 6) if col == 0 else (6, 0),
               sticky="ew")
        ctk.CTkLabel(f, text=label,
                     font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(pady=(8, 0))
        lbl = ctk.CTkLabel(f, text=value,
                           font=ctk.CTkFont(size=24, weight="bold"),
                           text_color=C_ACCENT)
        lbl.pack(pady=(0, 8))
        return lbl

    # ── Timer visual ──────────────────────────────────────────────────────────

    def _timer_tick(self):
        elapsed  = time.time() - self._last_reset_ts
        remaining = max(0, COOLDOWN_SECS - int(elapsed))

        if self._busy:
            self.lbl_timer.configure(text="Resetando...", text_color=C_YELLOW)
            self.timer_bar.set(1)
        elif remaining > 0:
            self.lbl_timer.configure(
                text=f"{remaining}s",
                text_color=C_YELLOW if remaining > 10 else C_RED)
            self.timer_bar.set(remaining / COOLDOWN_SECS)
        else:
            self.lbl_timer.configure(text="Pronto", text_color=C_GREEN)
            self.timer_bar.set(0)

        self.after(1000, self._timer_tick)

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log(self, msg, kind="info"):
        color = {"ok": C_GREEN, "err": C_RED, "warn": C_YELLOW}.get(kind, C_ACCENT)
        text  = f"> {msg}\n"

        def _insert():
            self.log_box.configure(state="normal")
            tag = f"t{time.monotonic_ns()}"
            self.log_box.tag_config(tag, foreground=color)
            self.log_box.insert("end", text, tag)
            self.log_box.configure(state="disabled")
            self.log_box.see("end")

        self.after(0, _insert)
        logging.info(msg)

    # ── Log toggle ────────────────────────────────────────────────────────────

    def _toggle_log(self):
        if self._log_open:
            self._log_open = False
            self._log_arrow.configure(text="▶")
            self._log_hint.configure(text="clique para expandir")
            self._animate_log(closing=True)
        else:
            self._log_open = True
            self._log_arrow.configure(text="▼")
            self._log_hint.configure(text="clique para recolher")
            self.log_box.pack(fill="x")
            self.log_box.see("end")
            self._log_height = 0
            self._animate_log(closing=False)

    def _animate_log(self, closing):
        if self._log_anim_id:
            self.after_cancel(self._log_anim_id)
        step = 20

        def _frame():
            if closing:
                self._log_height = max(0, self._log_height - step)
                if self._log_height <= 0:
                    self.log_box.pack_forget()
                    return
            else:
                self._log_height = min(self._log_target, self._log_height + step)
            self.log_box.configure(height=self._log_height)
            self.update_idletasks()
            if (closing and self._log_height > 0) or \
               (not closing and self._log_height < self._log_target):
                self._log_anim_id = self.after(10, _frame)

        self._log_height = self.log_box.winfo_height() if closing else 0
        _frame()

    # ── Progress ──────────────────────────────────────────────────────────────

    def _set_progress(self, pct, label=""):
        self.after(0, self.progressbar.set, pct / 100)
        if label:
            self.after(0, self.lbl_step.configure, {"text": label, "text_color": C_ACCENT})

    # ── Verificação inicial ───────────────────────────────────────────────────

    def _initial_check(self):
        self.after(0, self._start_spinner)
        self._log("Verificando AnyDesk...")
        time.sleep(0.8)
        if not anydesk_exe():
            self._log("AnyDesk não encontrado.", "warn")
            self.after(0, self.lbl_step.configure,
                       {"text": "AnyDesk não encontrado", "text_color": C_YELLOW})
        else:
            self._log("AnyDesk encontrado.", "ok")
            self.after(0, self.lbl_step.configure,
                       {"text": "Pronto para resetar", "text_color": C_GREEN})
        self.after(0, self._stop_spinner, True)

    # ── Notificação de cooldown ───────────────────────────────────────────────

    def _show_cooldown_notice(self, secs):
        d = ctk.CTkToplevel(self)
        d.title("")
        d.geometry("360x140")
        d.resizable(False, False)
        d.configure(fg_color=C_CARD)
        d.grab_set()
        try:
            if ICON_PATH.exists():
                d.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

        ctk.CTkLabel(d,
                     text="PARA MELHOR FUNCIONAMENTO DO APP",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_ACCENT).pack(pady=(20, 4))
        ctk.CTkLabel(d,
                     text=f"AGUARDE {secs} SEGUNDO(S) ATÉ OUTRO RESET",
                     font=ctk.CTkFont(size=11),
                     text_color=C_TEXT).pack()
        ctk.CTkButton(d, text="OK",
                      fg_color=C_ACCENT, hover_color=C_ACCENT2,
                      text_color="#0f172a",
                      height=30, corner_radius=6, width=80,
                      command=d.destroy).pack(pady=(14, 0))

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _on_reset(self, forced=False):
        if self._busy:
            return

        now = time.time()

        if not forced:
            elapsed = now - self._last_reset_ts
            if elapsed < COOLDOWN_SECS:
                remaining = int(COOLDOWN_SECS - elapsed)
                self._show_cooldown_notice(remaining)
                return

        if forced and self._force_session >= FORCE_LIMIT:
            self._show_cooldown_notice(0)
            self._log("Limite de reset forçado atingido. Reinicie a máquina.", "err")
            return

        # Se AnyDesk não estiver aberto, abre primeiro
        if not anydesk_process_running():
            self._log("AnyDesk não está aberto. Abrindo...", "warn")
            threading.Thread(target=self._open_then_reset,
                             args=(forced,), daemon=True).start()
        else:
            self._start_reset(forced)

    def _open_then_reset(self, forced):
        start_anydesk(self._log)
        # Aguarda processo iniciar
        for _ in range(15):
            if anydesk_process_running():
                break
            time.sleep(1)
        self.after(0, self._start_reset, forced)

    def _start_reset(self, forced):
        self._busy = True
        self.after(0, self.btn_reset.configure, {"state": "disabled"})
        self.after(0, self.btn_force.configure,  {"state": "disabled"})
        self.after(0, self.lbl_step.configure,   {"text": "Iniciando...", "text_color": C_ACCENT})
        self.after(0, self.progressbar.set, 0)
        self.after(0, self._start_spinner)
        threading.Thread(target=self._do_reset, args=(forced,), daemon=True).start()

    def _do_reset(self, forced):
        try:
            if forced:
                self._force_steps()
            else:
                self._normal_steps()
        except Exception as e:
            self._log(f"Erro inesperado: {e}", "err")
            logging.exception("Erro no reset")
        finally:
            self.after(0, self._finish, forced)

    # ── Reset normal ──────────────────────────────────────────────────────────

    def _normal_steps(self):
        self._log("Iniciando Reset...")
        self._set_progress(10, "Parando AnyDesk...")
        stop_service(self._log)
        self._set_progress(25, "Serviço parado.")

        self._set_progress(30, "Salvando preferências...")
        src = ANYDESK_USER / "user.conf"
        bak = TEMP_DIR / "anydesk_user_bak.conf"
        try:
            if src.exists():
                shutil.copy2(src, bak)
        except Exception as e:
            self._log(f"Aviso: {e}", "warn")

        self._set_progress(45, "Limpando configurações...")
        self._log("Removendo arquivos antigos...")
        for t in [ANYDESK_DATA / "service.conf", ANYDESK_USER / "service.conf"]:
            try: t.unlink(missing_ok=True)
            except Exception: pass
        for folder in [ANYDESK_DATA, ANYDESK_USER]:
            try:
                for f in folder.iterdir():
                    try:
                        if f.is_file(): f.unlink()
                    except Exception: pass
            except Exception: pass
        self._set_progress(55, "Arquivos limpos.")

        self._set_progress(60, "Gerando novo ID...")
        self._log("Iniciando AnyDesk para novo ID...")
        start_anydesk(self._log)
        new_id = get_new_id()
        if not new_id:
            self._log("Timeout ao gerar ID.", "err")
            self._set_progress(60, "Falha ao gerar ID.")
            return
        self._log(f"Novo ID: {new_id}", "ok")
        self._set_progress(75, f"ID: {new_id}")

        self._set_progress(85, "Restaurando preferências...")
        stop_service(self._log)
        try:
            if bak.exists():
                shutil.copy2(bak, ANYDESK_USER / "user.conf")
                bak.unlink(missing_ok=True)
                self._log("Preferências restauradas.", "ok")
        except Exception as e:
            self._log(f"Aviso: {e}", "warn")

        self._set_progress(92, "Reiniciando AnyDesk...")
        start_anydesk(self._log)
        self._set_progress(100, "Concluído!")
        self._log("Reset concluído.", "ok")

    # ── Forçar reset ──────────────────────────────────────────────────────────

    def _force_steps(self):
        self._log("Iniciando Forçar Reset — limpeza total...", "warn")
        self._set_progress(5, "Encerrando AnyDesk...")
        stop_service(self._log)
        self._set_progress(15, "Desinstalando AnyDesk...")
        self._log("Procurando desinstalador...")

        uninstalled = False
        for uninst in [
            Path(os.environ.get("ProgramFiles",      "")) / "AnyDesk/uninstall.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "AnyDesk/uninstall.exe",
        ]:
            if uninst.exists():
                self._log(f"Desinstalando via {uninst.name}...")
                run([str(uninst), "--mode", "unattended"], timeout=60)
                uninstalled = True
                time.sleep(3)
                break

        if not uninstalled:
            self._log("Usando wmic para desinstalar...", "warn")
            run(["wmic", "product", "where", "name like '%AnyDesk%'",
                 "call", "uninstall", "/nointeractive"], timeout=90)
            time.sleep(3)

        self._set_progress(35, "Removendo arquivos residuais...")
        for d in [ANYDESK_DATA, ANYDESK_USER,
                  Path(os.environ.get("ProgramFiles",      "")) / "AnyDesk",
                  Path(os.environ.get("ProgramFiles(x86)", "")) / "AnyDesk",
                  Path(os.environ.get("LOCALAPPDATA",      "")) / "AnyDesk"]:
            try:
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)
                    self._log(f"Removido: {d.name}", "info")
            except Exception as e:
                self._log(f"Aviso: {e}", "warn")

        self._set_progress(50, "Limpando registro...")
        try:
            for hive, key in [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\AnyDesk"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\AnyDesk"),
                (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\AnyDesk"),
            ]:
                try:
                    winreg.DeleteKey(hive, key)
                except FileNotFoundError:
                    pass
        except Exception:
            pass
        self._set_progress(62, "Registro limpo.")

        # Instala AnyDesk local ou baixa
        self._set_progress(65, "Instalando AnyDesk limpo...")
        if ANYDESK_INST.exists():
            installer = ANYDESK_INST
            self._log("Usando instalador local...")
        else:
            self._log("Baixando AnyDesk...")
            installer = APP_DIR / "AnyDesk_fresh.exe"
            ok = download_file(ANYDESK_URL, installer)
            if not ok:
                self._log("Download falhou.", "err")
                self._set_progress(65, "Falha no download.")
                return

        self._set_progress(78, "Instalando AnyDesk no sistema...")
        self._log("Instalando AnyDesk de forma permanente no PC...")
        ret = run([str(installer),
                   "--install",
                   "--silent",
                   "--create-shortcuts",
                   "--create-desktop-icon",
                   "--start-with-win"], timeout=180)
        if ret not in (0, 1):
            self._log(f"Aviso: instalador retornou {ret}.", "warn")
        if installer != ANYDESK_INST:
            installer.unlink(missing_ok=True)
        time.sleep(4)

        self._set_progress(90, "Iniciando AnyDesk...")
        start_anydesk(self._log)
        new_id = get_new_id()
        if new_id:
            self._log(f"Novo ID: {new_id}", "ok")
        self._set_progress(100, "Forçar Reset concluído!")
        self._log("AnyDesk reinstalado do zero.", "ok")

    # ── Finish ────────────────────────────────────────────────────────────────

    def _finish(self, forced):
        self._busy = False
        if forced:
            self._force_count   += 1
            self._force_session += 1
            count = self._force_count
            self.after(0, lambda: self._lbl_forced.configure(text=str(count)))
            if self._force_session >= FORCE_LIMIT:
                self.after(0, self.btn_force.configure,
                           {"state": "disabled", "text": "⚡  Limite atingido"})
            else:
                self.after(0, self.btn_force.configure, {"state": "normal"})
        else:
            self._reset_count  += 1
            self._last_reset_ts = time.time()
            count = self._reset_count
            self.after(0, lambda: self._lbl_resets.configure(text=str(count)))
            self.after(0, self.btn_force.configure, {"state": "normal"})

        save_history(self._reset_count, self._force_count)
        self.after(0, self.btn_reset.configure, {"state": "normal"})
        self.after(0, self._stop_spinner, True)
        self.after(0, self.lbl_step.configure, {"text": "Concluído!", "text_color": C_GREEN})


# ═══════════════════════════════════════════════════════════════════════════════
# SPLASH (verificação rápida nas execuções seguintes)
# ═══════════════════════════════════════════════════════════════════════════════

class SplashCheck(ctk.CTkToplevel):
    """Verificação rápida 2s — garante que tudo está ok antes de abrir."""

    def __init__(self, master, on_ok, on_need_setup):
        super().__init__(master)
        self._on_ok         = on_ok
        self._on_need_setup = on_need_setup

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 340, 160
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.overrideredirect(True)

        ctk.CTkLabel(self, text="Reset AnyDesk",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C_ACCENT).pack(pady=(28, 4))
        self.lbl = ctk.CTkLabel(self, text="Verificando...",
                                 font=ctk.CTkFont(size=11),
                                 text_color=C_MUTED)
        self.lbl.pack()
        self.bar = ctk.CTkProgressBar(self, progress_color=C_ACCENT,
                                       fg_color=C_CARD2, height=4,
                                       corner_radius=0)
        self.bar.pack(fill="x", padx=30, pady=(12, 0))
        self.bar.set(0)

        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        steps = [
            (0.3, "Verificando AnyDesk..."),
            (0.6, "Verificando ambiente..."),
            (1.0, "Pronto!"),
        ]
        for pct, msg in steps:
            self.after(0, self.bar.set, pct)
            self.after(0, self.lbl.configure, {"text": msg})
            time.sleep(0.4)

        # Verifica se precisa de setup
        ver = anydesk_installed_version()
        needs = (ver != ANYDESK_VERSION or not SETUP_FLAG.exists())

        self.after(0, self.destroy)
        if needs:
            self.after(0, self._on_need_setup)
        else:
            self.after(0, self._on_ok)


# ═══════════════════════════════════════════════════════════════════════════════
# ORQUESTRADOR
# ═══════════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    """Janela raiz invisível que orquestra o fluxo."""

    def __init__(self):
        super().__init__()
        self.withdraw()   # fica invisível
        self.title("Reset AnyDesk")
        copy_icon_to_appdir()
        self._start_flow()

    def _start_flow(self):
        first_run = not SETUP_FLAG.exists()

        if first_run:
            # Primeira vez → setup completo
            SetupWindow(self, on_complete=self._open_main)
        else:
            # Execuções seguintes → splash rápido
            SplashCheck(self,
                        on_ok=self._open_main,
                        on_need_setup=lambda: SetupWindow(self, on_complete=self._open_main))

    def _open_main(self):
        main = MainWindow()
        main.protocol("WM_DELETE_WINDOW", lambda: (main.destroy(), self.destroy()))
        main.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
