from gologin import GoLogin

gl_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MzE5YjkyZjcxMzEyNjM3NDkyYzhiNDgiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2MzI1MWVhN2NlZWRiZWMxNGU4OTRhZTkifQ.Gb92xRhbQTcUMjjzMuyq7uEl31r4GA0EJ1211X2vzwU'
profileid = '66e3afec981ab44dd2318c29' # <- I've preloaded cookies into this profile.

gl = GoLogin({
    'token': gl_token,
    'profile_id': profileid,
    'executablePath': '/Users/thatkit/.gologin/browser/orbita-browser-128/Orbita-Browser.app/Contents/MacOS/Orbita',
    'restore_last_session': True,
    'writeCookiesFromServer': True,
})

debugger_address = gl.start()
