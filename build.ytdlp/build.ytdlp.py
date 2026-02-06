import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import ctypes
import time
import threading
import stat
import glob
import winreg
from datetime import datetime

# ==============================================================================
#                               DISEÑO VISUAL (THEME)
# ==============================================================================
try:
    ctypes.windll.kernel32.SetConsoleTitleW("Flux Builder - Official Release (Patched)")
except:
    pass

class JF_Theme:
    CYAN = '\033[38;5;51m'
    PURPLE = '\033[38;5;141m'
    GREEN = '\033[38;5;82m'
    GOLD = '\033[38;5;220m' 
    RED = '\033[38;5;196m'
    GREY = '\033[38;5;240m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    BANNER = f"""
    {PURPLE}   ███████╗██╗     ██╗   ██╗██╗  ██╗
    ██╔════╝██║     ██║   ██║╚██╗██╔╝
    █████╗  ██║     ██║   ██║ ╚███╔╝ 
    ██╔══╝  ██║     ██║   ██║ ██╔██╗ 
    ██║     ███████╗╚██████╔╝██╔╝ ██╗
    ╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
    {CYAN}    >> ONE CLICK COMPILER FOR YT-DPL - by JamFlux << {RESET}"""

# ==============================================================================
#                               CLASE ANIMACIÓN (SPINNER)
# ==============================================================================
class Spinner:
    def __init__(self, message="Procesando...", color=JF_Theme.CYAN):
        self.message = message
        self.color = color
        self.busy = False
        self.delay = 0.1
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
    def spinner_task(self):
        while self.busy:
            for char in self.spinner_chars:
                sys.stdout.write(f'\r {self.color}{char}{JF_Theme.RESET} {self.message}')
                sys.stdout.flush()
                time.sleep(self.delay)
                if not self.busy: break
                
    def __enter__(self):
        self.busy = True
        self.t = threading.Thread(target=self.spinner_task)
        self.t.start()
        return self

    def __exit__(self, exception, value, tb):
        self.busy = False
        time.sleep(self.delay)
        if exception:
            sys.stdout.write(f'\r {JF_Theme.RED}✖{JF_Theme.RESET} {self.message} -> {JF_Theme.RED}FALLÓ{JF_Theme.RESET}\n')
        else:
            sys.stdout.write(f'\r {JF_Theme.GREEN}✔{JF_Theme.RESET} {self.message} -> {JF_Theme.GREEN}COMPLETADO{JF_Theme.RESET}\n')
        sys.stdout.flush()

def draw_interface(step_name, progress_percent):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(JF_Theme.BANNER)
    print(f"{JF_Theme.PURPLE}{'='*60}{JF_Theme.RESET}\n")
    
    width = 40
    filled = int(width * progress_percent // 100)
    bar = f"{JF_Theme.GREEN}━{JF_Theme.RESET}" * filled + f"{JF_Theme.GREY}━{JF_Theme.RESET}" * (width - filled)
    
    print(f"  {JF_Theme.BOLD}PROGRESO GENERAL:{JF_Theme.RESET}  {progress_percent}%")
    print(f"  {bar}\n")
    print(f"  {JF_Theme.BOLD}TAREA ACTUAL:{JF_Theme.RESET}      {JF_Theme.GOLD}{step_name}{JF_Theme.RESET}\n")
    print(f"{JF_Theme.PURPLE}{'-'*60}{JF_Theme.RESET}\n")

# ==============================================================================
#                               LOGICA INTERNA
# ==============================================================================

def run_command_silent(cmd, cwd=None):
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    proc = subprocess.run(
        cmd, 
        cwd=cwd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True,
        startupinfo=startupinfo
    )
    
    if proc.returncode != 0:
        raise Exception(f"Error en comando: {' '.join(cmd)}\n{proc.stderr}")

# --- DETECCIÓN BLINDADA DE PYTHON (FIX WINDOWS APPS) ---
def validar_python(path):
    if not path or not os.path.exists(path): return False
    if "WindowsApps" in path: return False # Bloqueo explícito a la tienda
    try:
        res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0: return True
    except: return False
    return False

def encontrar_python():
    # 1. Si ejecutamos desde .py, probar el actual
    if not getattr(sys, 'frozen', False):
        if validar_python(sys.executable): return sys.executable

    candidatos = []
    
    # 2. Rutas comunes
    user_path = os.path.expanduser("~")
    common_paths = [
        os.path.join(user_path, r"AppData\Local\Programs\Python"),
        r"C:\Program Files\Python",
        r"C:\Python"
    ]
    for root in common_paths:
        if os.path.exists(root):
            for item in glob.glob(os.path.join(root, "Python3*")):
                exe = os.path.join(item, "python.exe")
                if os.path.exists(exe): candidatos.append(exe)

    # 3. Registro de Windows
    hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    for hive in hives:
        try:
            key = winreg.OpenKey(hive, r"SOFTWARE\Python\PythonCore")
            i = 0
            while True:
                try:
                    ver = winreg.EnumKey(key, i)
                    path_key = winreg.OpenKey(key, f"{ver}\\InstallPath")
                    val, _ = winreg.QueryValueEx(path_key, "")
                    exe = os.path.join(val, "python.exe")
                    if validar_python(exe): candidatos.append(exe)
                    i += 1
                except OSError: break
        except: pass

    # 4. Filtrar candidatos
    for py in candidatos:
        if validar_python(py): return py

    raise Exception("No se encontró una instalación de Python válida (No WindowsApps). Instala Python desde python.org")

def descargar_upx():
    if os.path.exists("upx.exe"): return
    url = "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip"
    urllib.request.urlretrieve(url, "upx.zip")
    with zipfile.ZipFile("upx.zip", 'r') as z:
        for f in z.namelist():
            if f.endswith("upx.exe"):
                with open("upx.exe", "wb") as dest:
                    dest.write(z.read(f))
                break
    try: os.remove("upx.zip") 
    except: pass

def force_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except: pass 

def limpiar_area():
    items = [
        "build", "dist", "yt-dlp-master", "devscripts", "yt_dlp", "bundle",
        "source.zip", "version_info.txt", "upx.exe", "upx.zip", "yt-dlp.spec"
    ]
    time.sleep(1)
    for item in items:
        if os.path.exists(item):
            try:
                if os.path.isdir(item): shutil.rmtree(item, onerror=force_remove_readonly)
                else: os.remove(item)
            except:
                if os.name == 'nt':
                    subprocess.run(f'del /f /q "{item}"' if os.path.isfile(item) else f'rmdir /s /q "{item}"', shell=True, stdout=subprocess.DEVNULL)

def aplicar_parche_seguridad(repo_dir):
    """
    Edita el script oficial bundle/pyinstaller.py para evitar el crash de WinError 2.
    Envuelve la llamada set_version_info en un try-except.
    """
    target_file = os.path.join(repo_dir, "bundle", "pyinstaller.py")
    if not os.path.exists(target_file):
        return # Si cambia la estructura en el futuro, no rompemos nada, solo seguimos
        
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Buscamos la línea conflictiva
        original_code = "set_version_info(final_file, version)"
        patched_code = """
    try:
        set_version_info(final_file, version)
    except Exception as e:
        print(f"FluxPatch Warning: Version info could not be set: {e}")
        """
        
        if original_code in content:
            content = content.replace(original_code, patched_code)
            
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
    except:
        return False
    return False

# ==============================================================================
#                               MAIN
# ==============================================================================
def main():
    start_time = time.time()
    
    try:
        draw_interface("Limpiando zona de trabajo...", 0)
        limpiar_area()
        
        draw_interface("Buscando Python real...", 5)
        py_exe = encontrar_python()
        
        # 1. PREPARACIÓN DE ENTORNO
        draw_interface("Verificando herramientas...", 10)
        with Spinner(f"Usando motor: {os.path.basename(py_exe)}..."):
            descargar_upx()
            # Añadir UPX al path actual para que el bundle oficial lo vea
            os.environ["PATH"] += os.pathsep + os.getcwd()

        # 2. DESCARGA
        draw_interface("Descargando código fuente...", 25)
        with Spinner("Bajando Master Branch de GitHub..."):
            urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip", "source.zip")
            with zipfile.ZipFile("source.zip", 'r') as z: z.extractall(".")
        
        repo_dir = os.path.abspath("yt-dlp-master")
        if not os.path.exists(repo_dir): raise Exception("Fallo al descomprimir.")

        # --- FASE DE PARCHEO ---
        draw_interface("Aplicando parches de seguridad...", 35)
        with Spinner("Blindando script oficial contra errores de Windows..."):
            aplicar_parche_seguridad(repo_dir)

        # 3. DEPENDENCIAS
        draw_interface("Configurando dependencias...", 45)
        with Spinner("Instalando librerías oficiales..."):
            # python devscripts/install_deps.py --include-extra pyinstaller
            script = os.path.join(repo_dir, "devscripts", "install_deps.py")
            run_command_silent([py_exe, script, "--include-extra", "pyinstaller"])

        # 4. OPTIMIZACIÓN
        draw_interface("Optimizando código...", 65)
        with Spinner("Generando extractores perezosos (Lazy Extractors)..."):
            script = os.path.join(repo_dir, "devscripts", "make_lazy_extractors.py")
            run_command_silent([py_exe, script], cwd=repo_dir)

        # 5. COMPILACIÓN OFICIAL
        draw_interface("Compilando binario final...", 85)
        with Spinner("Empaquetando con PyInstaller + UPX..."):
            # El script oficial detecta UPX automáticamente si está en PATH o carpeta
            run_command_silent([py_exe, "-m", "bundle.pyinstaller"], cwd=repo_dir)

        # 6. FINALIZACIÓN
        draw_interface("Finalizando...", 95)
        src_exe = os.path.join(repo_dir, "dist", "yt-dlp.exe")
        target_exe = "yt-dlp.exe"
        
        if os.path.exists(src_exe):
            if os.path.exists(target_exe): 
                try: os.remove(target_exe)
                except: pass 
                
            shutil.move(src_exe, target_exe)
            
            with Spinner("Ejecutando limpieza profunda..."):
                limpiar_area()
            
            size = os.path.getsize(target_exe) / (1024*1024)
            draw_interface("¡PROCESO COMPLETADO!", 100)
            print(f"\n  {JF_Theme.GREEN}✔ ARCHIVO GENERADO:{JF_Theme.RESET} {target_exe}")
            print(f"  {JF_Theme.GOLD}⚖ TAMAÑO FINAL:{JF_Theme.RESET}     {size:.2f} MB")
            print(f"  {JF_Theme.CYAN}⏱ TIEMPO TOTAL:{JF_Theme.RESET}     {int(time.time() - start_time)} segundos\n")
            
        else:
            raise Exception("No se generó el archivo .exe final.")

    except Exception as e:
        limpiar_area()
        print(f"\n\n{JF_Theme.RED}ERROR FATAL:{JF_Theme.RESET} {e}")
        input()

if __name__ == "__main__":
    main()