import threading
import subprocess
import sys


def run_bot():
    subprocess.run([sys.executable, "main.py"])


def run_admin_panel():
    subprocess.run([sys.executable, "admin_panel.py"])


if __name__ == "__main__":
    t1 = threading.Thread(target=run_bot)
    t2 = threading.Thread(target=run_admin_panel)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
