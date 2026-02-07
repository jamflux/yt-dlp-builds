import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import glob
import ctypes
import time
import winreg

# ==============================================================================
#                               CONFIGURACIÓN VISUAL
# ==============================================================================
try:
    ctypes.windll.kernel32.SetConsoleTitleW("Flux Builder - Official Final Fix")
except:
    pass

class JF_Theme:
    CYAN = '\033[38;5;51m'
    PURPLE = '\033[38;5;141m'
    GREEN = '\033[38;5;82m'
    GOLD = '\033[38;5;220m' 
    RED = '\033[38;5;196m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    BANNER = f"""
{PURPLE}{'='*63}{RESET}
{CYAN}    >> ONE CLICK YT-DLP BUILDER - FLUX DIGITAL - JAMFLUX << {RESET}"""

def jf_refresh(status_msg, progress=0):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(JF_Theme.BANNER)
    print(f"{JF_Theme.PURPLE}{'='*63}{JF_Theme.RESET}\n")
    print(f" {JF_Theme.BOLD}{JF_Theme.GOLD}[ FASE ]:{JF_Theme.RESET} {JF_Theme.CYAN}{status_msg}{JF_Theme.RESET}\n")
    filled = int(35 * progress // 100)
    bar = f"{JF_Theme.GREEN}█{JF_Theme.RESET}" * filled + f"{JF_Theme.PURPLE}░{JF_Theme.RESET}" * (35 - filled)
    print(f" {bar} {JF_Theme.BOLD}{progress}%{JF_Theme.RESET}\n")

# ==============================================================================
#                               LÓGICA DEL SISTEMA
# ==============================================================================

def run_silent(cmd, cwd=None, env=None):
    try:
        subprocess.run(
            cmd, 
            cwd=cwd, 
            env=env, 
            check=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else "Error desconocido"
        raise Exception(f"Fallo en: {cmd[0] if isinstance(cmd, list) else cmd}\nDetalle: {error_msg}")

def validar_python(path):
    if not path or not os.path.exists(path): return False
    if "WindowsApps" in path: return False 
    try:
        res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0: return True
    except: return False
    return False

def encontrar_python_real():
    if not getattr(sys, 'frozen', False):
        if validar_python(sys.executable): return sys.executable

    candidatos = []
    user_path = os.path.expanduser("~")
    rutas_comunes = [
        os.path.join(user_path, r"AppData\Local\Programs\Python"),
        r"C:\Program Files\Python",
        r"C:\Python"
    ]
    for root in rutas_comunes:
        if os.path.exists(root):
            for item in glob.glob(os.path.join(root, "Python3*")):
                exe = os.path.join(item, "python.exe")
                if os.path.exists(exe): candidatos.append(exe)

    try:
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
    except: pass

    for py in candidatos:
        if validar_python(py): return py

    if shutil.which("python") and validar_python(shutil.which("python")):
        return shutil.which("python")

    raise Exception("No se encontró Python instalado. Instálalo desde python.org")

def setup_upx():
    if os.path.exists("upx.exe"): return True
    try:
        url = "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip"
        urllib.request.urlretrieve(url, "upx.zip")
        with zipfile.ZipFile("upx.zip", 'r') as z:
            for f in z.namelist():
                if f.endswith("upx.exe"):
                    with open("upx.exe", "wb") as dest: dest.write(z.read(f))
                    break
        try: os.remove("upx.zip")
        except: pass
        return True
    except: return False

def cleanup():
    folders = ["build", "dist", "yt-dlp-master", "devscripts", "yt_dlp", "bundle"]
    for c in folders:
        if os.path.exists(c):
            try: shutil.rmtree(c, ignore_errors=True)
            except: pass
    files = ["source.zip", "upx.zip", "upx.exe", "yt-dlp.spec"]
    for f in files:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

# ==============================================================================
#                               CORRECCIÓN DE RUTA (SIN ROMPER CÓDIGO)
# ==============================================================================

def arreglar_ruta_metadatos(repo_dir):
    """
    Modifica bundle/pyinstaller.py para usar RUTAS ABSOLUTAS.
    IMPORTANTE: No inyectamos 'import os' porque ya existe globalmente.
    """
    bundler = os.path.join(repo_dir, "bundle", "pyinstaller.py")
    if os.path.exists(bundler):
        with open(bundler, "r", encoding="utf-8") as f:
            code = f.read()
        
        target = "set_version_info(final_file, version)"
        # FIX: Solo forzamos path absoluto, asumiendo que 'os' ya está importado (que lo está).
        fix = "final_file = os.path.abspath(final_file); set_version_info(final_file, version)"
        
        if target in code:
            code = code.replace(target, fix)
            with open(bundler, "w", encoding="utf-8") as f:
                f.write(code)
            return True
    return False

# ==============================================================================
#                               MAIN
# ==============================================================================
def main():
    try:
        py = encontrar_python_real()
        cleanup()
        
        jf_refresh("Cargando motor UPX...", 10)
        has_upx = setup_upx()
        
        env = os.environ.copy()
        if has_upx: 
            env["PATH"] = os.getcwd() + os.pathsep + env["PATH"]
        
        jf_refresh("Descargando código oficial...", 25)
        urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip", "source.zip")
        with zipfile.ZipFile("source.zip", 'r') as z: z.extractall(".")
        
        repo = os.path.abspath("yt-dlp-master")
        
        # Aplicamos la corrección para que Windows no pierda el archivo al final
        arreglar_ruta_metadatos(repo)
        
        jf_refresh("Instalando dependencias...", 45)
        deps = ["mutagen", "pycryptodomex", "websockets", "brotli", "certifi", "requests", "pyinstaller"]
        run_silent([py, "-m", "pip", "install"] + deps + ["--disable-pip-version-check"])
        
        jf_refresh("Optimizando (Lazy Extractors)...", 60)
        run_silent([py, "devscripts/make_lazy_extractors.py"], cwd=repo)
        
        jf_refresh("Compilando Binario Oficial...", 80)
        run_silent([py, "-m", "bundle.pyinstaller"], cwd=repo, env=env)
        
        jf_refresh("Finalizando...", 95)
        src = os.path.join(repo, "dist", "yt-dlp.exe")
        dst = "yt-dlp.exe"
        
        if os.path.exists(src):
            if os.path.exists(dst): os.remove(dst)
            shutil.move(src, dst)
            size = os.path.getsize(dst) / (1024 * 1024)
            cleanup()
            
            # Semáforo de peso
            col = JF_Theme.GREEN if size < 25 else JF_Theme.RED
            jf_refresh(f"¡HECHO! Peso: {col}{size:.2f} MB{JF_Theme.RESET}", 100)
            
            print(f"\n  {JF_Theme.CYAN}Estado:{JF_Theme.RESET}    Compilación Oficial Exitosa")
            print(f"  {JF_Theme.GOLD}Motor:{JF_Theme.RESET}     {os.path.basename(py)}")
            print(f"  {JF_Theme.GOLD}Tamaño:{JF_Theme.RESET}    {col}{size:.2f} MB{JF_Theme.RESET}")
            
            if size > 25:
                print(f"\n  {JF_Theme.RED}⚠  ADVERTENCIA:{JF_Theme.RESET} El archivo supera los 25MB.")
            else:
                print(f"\n  {JF_Theme.GREEN}✔  EXCELENTE:{JF_Theme.RESET} Apto para GitHub (<25MB).")
                
            time.sleep(5)
        else:
            print(f"\n {JF_Theme.RED}[ERROR] No se generó el EXE.{JF_Theme.RESET}")
            input()

    except Exception as e:
        print(f"\n{JF_Theme.RED}ERROR CRITICO:{JF_Theme.RESET} {e}")
        input()

if __name__ == "__main__":
    main()