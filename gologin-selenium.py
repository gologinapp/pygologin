import time
from sys import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from gologin import GoLogin
from gologin import get_random_port

# random_port = get_random_port() # uncomment to use random port

gl = GoLogin({
	"token": "yU0token",
	"profile_id": "yU0Pr0f1leiD",
	# "port": random_port
	})

if platform == "linux" or platform == "linux2":
	chrome_driver_path = "./chromedriver"
elif platform == "darwin":
	chrome_driver_path = "./mac/chromedriver"
elif platform == "win32":
	chrome_driver_path = "chromedriver.exe"

debugger_address = gl.start()
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", debugger_address)
driver = webdriver.Chrome(executable_path=chrome_driver_path, options=chrome_options)
driver.get("http://www.python.org")
assert "Python" in driver.title
driver.close()
time.sleep(3)
gl.stop()
