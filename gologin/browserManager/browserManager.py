import os
import pathlib
import requests
import sys
import zipfile
import platform
import subprocess
import shutil
import time
import fcntl
import errno
class BrowserManager:
    def __init__(self):
        self.home = str(pathlib.Path.home())
        self.browser_dir = os.path.join(self.home, '.gologin', 'browser')
        os.makedirs(self.browser_dir, exist_ok=True)
        
    def get_orbita_path(self, major_version: int):
        browsers = os.listdir(self.browser_dir)
        matching_browsers = [browser for browser in browsers if browser.endswith(str(major_version))]
        installedFolder = matching_browsers[0] if matching_browsers else None

        if installedFolder is None:
            self.download_and_install(major_version)
            browsers = os.listdir(self.browser_dir)
            [installedFolder] = [browser for browser in browsers if browser.endswith(str(major_version))]

        resultPath = os.path.join(self.browser_dir, installedFolder)
        if sys.platform == "win32":
            executable_path = os.path.join(resultPath, "chrome.exe")
        elif sys.platform == "darwin":
            executable_path = os.path.join(resultPath, "Orbita-Browser.app", "Contents", "MacOS", "Orbita")
        else:
            executable_path = os.path.join(resultPath, "chrome")
        
        return executable_path

    def download_and_install(self, major_version: int):
        lock_file_path = os.path.join(self.browser_dir, f"orbita-download-lock-{major_version}.lock")
        lock_file = None
        
        try:
            lock_file = self._acquire_lock(lock_file_path, major_version)
            os.makedirs(self.browser_dir, exist_ok=True)
            
            browsers = os.listdir(self.browser_dir)
            matching_browsers = [browser for browser in browsers if browser.endswith(str(major_version))]
            if matching_browsers:
                return
            
            download_url = f"https://orbita-browser-linux.gologin.com/orbita-browser-latest-{major_version}.tar.gz"
            file_extension = 'tar.gz'
            if sys.platform == "darwin":
                download_url = f"https://orbita-browser-mac.gologin.com/orbita-browser-latest-{major_version}.tar.gz"
                is_arm = platform.machine() == 'arm64'
                if is_arm:
                    download_url = f"https://orbita-browser-mac-arm.gologin.com/orbita-browser-latest-{major_version}.tar.gz"
                
            if sys.platform == "win32":
                download_url = f"https://orbita-browser-windows.gologin.com/orbita-browser-latest-{major_version}.zip"
                file_extension = 'zip'
            print(f"Downloading Orbita browser version {major_version} from {download_url}")

            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            temp_file = os.path.join(self.browser_dir, f"orbita-browser-temp.{file_extension}")
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            extracted_dir = os.path.join(self.browser_dir, f"orbita-browser-{major_version}")
            os.makedirs(extracted_dir, exist_ok=True)
            if sys.platform == "win32":
                temp_extract_dir = os.path.join(self.browser_dir, f"temp-extract-{major_version}")
                os.makedirs(temp_extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                subfolders = [f for f in os.listdir(temp_extract_dir) if os.path.isdir(os.path.join(temp_extract_dir, f))]
                
                if subfolders:
                    subfolder_path = os.path.join(temp_extract_dir, subfolders[0])
                    for item in os.listdir(subfolder_path):
                        shutil.move(
                            os.path.join(subfolder_path, item),
                            os.path.join(extracted_dir, item)
                        )
                
                shutil.rmtree(temp_extract_dir)
            elif sys.platform == "darwin":
                subprocess.run(['tar', '-xzf', temp_file, '-C', extracted_dir], check=True)
            else:
                temp_extract_dir = os.path.join(self.browser_dir, f"temp-extract-{major_version}")
                os.makedirs(temp_extract_dir, exist_ok=True)
                subprocess.run(['tar', '-xzf', temp_file, '-C', temp_extract_dir], check=True)
                subfolders = [f for f in os.listdir(temp_extract_dir) if os.path.isdir(os.path.join(temp_extract_dir, f))]
                
                if subfolders:
                    subfolder_path = os.path.join(temp_extract_dir, subfolders[0])
                    for item in os.listdir(subfolder_path):
                        shutil.move(
                            os.path.join(subfolder_path, item),
                            os.path.join(extracted_dir, item)
                        )
                
                shutil.rmtree(temp_extract_dir)
                
            os.remove(temp_file)
            
        finally:
            self._release_lock(lock_file, lock_file_path)

    def _acquire_lock(self, lock_file_path: str, major_version: int):
        max_wait_time = 300
        check_interval = 1
        waited_time = 0
        
        while waited_time < max_wait_time:
            try:
                lock_file = open(lock_file_path, 'w')
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_file.write(f"{os.getpid()}\n")
                lock_file.flush()
                return lock_file
            except (OSError, IOError) as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
                    if os.path.exists(lock_file_path):
                        try:
                            with open(lock_file_path, 'r') as f:
                                pid = f.read().strip()
                                if pid and self._is_process_running(int(pid)):
                                    print(f"Waiting for Orbita browser version {major_version} download to complete...")
                                    time.sleep(check_interval)
                                    waited_time += check_interval
                                    continue
                                else:
                                    os.remove(lock_file_path)
                        except (ValueError, OSError):
                            os.remove(lock_file_path)
                    else:
                        time.sleep(check_interval)
                        waited_time += check_interval
                else:
                    raise
        
        raise Exception(f"Timeout waiting for Orbita browser version {major_version} download lock")

    def _release_lock(self, lock_file, lock_file_path: str):
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except (OSError, IOError):
                pass
        
        try:
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
        except OSError:
            pass

    def _is_process_running(self, pid: int):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False