import time
from gologin import GoLogin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
profile_id = "Your profile id"

# Initialize GoLogin
gl = GoLogin({
	"token": "Your token",
	"profile_id": profile_id
	})

# Start Browser and get websocket url
debugger_address = gl.start()

# Get Chromium version for webdriver
chromium_version = gl.get_chromium_version()

# Add proxy to profile
gl.addGologinProxyToProfile(profile_id, "us")

# Install webdriver
service = Service(ChromeDriverManager(driver_version=chromium_version).install())

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("debuggerAddress", debugger_address)

driver = webdriver.Chrome(service=service, options=chrome_options)
gl = GoLogin({
	"token": "your token",
	})
profile = gl.createProfileRandomFingerprint({"os": "lin", "name": "some name"})
gl.setProfileId(profile['id'])
# Give command to Selenium to open the page
driver.get("http://www.python.org")

time.sleep(30)
driver.quit()
time.sleep(10)
gl.stop()
