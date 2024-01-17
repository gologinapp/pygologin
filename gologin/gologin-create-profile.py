from gologin import GoLogin


gl = GoLogin({
	"token": "yU0token",
	})

profile_id = gl.create({
    "name": 'profile_mac',
    "os": 'mac',
    "navigator": {
        "language": 'en-US',
        "userAgent": 'random',
        "resolution": '1024x768',
        "platform": 'mac',
    },
    'proxy': {
        'mode': 'gologin', # Specify 'none' if not using proxy
        'autoProxyRegion': 'us' 
        # "host": '',
        # "port": '',
        # "username": '',
        # "password": '',
    },
    "webRTC": {
        "mode": "alerted",
        "enabled": True,
    },
    "storage": {
        "local":        True,   # Local Storage is special browser caches that websites may use for user tracking in a way similar to cookies. 
                                # Having them enabled is generally advised but may increase browser profile loading times.
  
        "extensions":   True,   # Extension storage is a special cotainer where a browser stores extensions and their parameter. 
                                # Enable it if you need to install extensions from a browser interface.
                            
        "bookmarks":    True,   # This option enables saving bookmarks in a browser interface.
                            
        "history":      True,   # Warning! Enabling this option may increase the amount of data required 
                                # to open/save a browser profile significantly. 
                                # In the interests of security, you may wish to disable this feature, 
                                # but it may make using GoLogin less convenient.
                             
        "passwords":    True,   # This option will save passwords stored in browsers.
                                # It is used for pre-filling login forms on websites. 
                                # All passwords are securely encrypted alongside all your data.
                             
        "session":      True,   # This option will save browser session. It is used to save last open tabs.
                            
        "indexedDb":    False   # IndexedDB is special browser caches that websites may use for user tracking in a way similar to cookies. 
                                # Having them enabled is generally advised but may increase browser profile loading times.
    }
});

print('profile id=', profile_id);

# gl.update({
#     "id": 'yU0Pr0f1leiD',
#     "name": 'profile_mac2',
# });

profile = gl.getProfile(profile_id);

print('new profile name=', profile.get("name"));

# gl.delete('yU0Pr0f1leiD')
