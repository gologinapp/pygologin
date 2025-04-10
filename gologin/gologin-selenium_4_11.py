import time
from sys import platform
from selenium import webdriver
from gologin import GoLogin
from gologin import getRandomPort
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

gl = GoLogin({
	"token": "Your token",
	"profile_id": "Your profile id"
	})

debugger_address = gl.start()
chromium_version = gl.get_chromium_version()
service = Service(ChromeDriverManager(driver_version=chromium_version).install())

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("debuggerAddress", debugger_address)

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get("http://www.python.org")

time.sleep(30)
driver.quit()
time.sleep(10)
gl.stop()
