import time
from sys import platform
from selenium import webdriver
from gologin import GoLogin
from gologin import getRandomPort
from selenium.webdriver.chrome.service import Service

gl = GoLogin({
	"token": "yU0token",
	"profile_id": "yU0Pr0f1leiD"
	})

if platform == "linux" or platform == "linux2":
	chrome_driver_path = "./chromedriver"
elif platform == "darwin":
	chrome_driver_path = "./mac/chromedriver"
elif platform == "win32":
	chrome_driver_path = "chromedriver.exe"

debugger_address = gl.start()
service = Service(executable_path=chrome_driver_path)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("debuggerAddress", debugger_address)

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get("http://www.python.org")

time.sleep(30)
driver.quit()
time.sleep(10)
gl.stop()
