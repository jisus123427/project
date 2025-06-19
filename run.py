import threading
import subprocess
import sys
import os
import time
import psutil
import requests
from requests.exceptions import RequestException

def install_requirements():
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        return False

def is_service_ready(url, max_attempts=30):
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(f"{url}/health")
            if response.status_code == 200:
                return True
        except RequestException:
            pass
        attempt += 1
        time.sleep(1)
    return False

def run_ocr_service():
    try:
        subprocess.run([sys.executable, "ocr_service.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass

def run_telegram_bot():
    try:
        subprocess.run([sys.executable, "tg-bot.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass

def kill_processes_on_ports(ports):
    for port in ports:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            psutil.Process(proc.pid).terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

def main():
    if not install_requirements():
        return
    kill_processes_on_ports([8000])
    time.sleep(1)
    ocr_thread = threading.Thread(target=run_ocr_service)
    telegram_thread = threading.Thread(target=run_telegram_bot)
    try:
        ocr_thread.start()
        if not is_service_ready("http://localhost:8000"):
            sys.exit(1)
        telegram_thread.start()
        ocr_thread.join()
        telegram_thread.join()
    except KeyboardInterrupt:
        kill_processes_on_ports([8000])
        sys.exit(0)
    except Exception:
        kill_processes_on_ports([8000])
        sys.exit(1)

if __name__ == "__main__":
    main() 