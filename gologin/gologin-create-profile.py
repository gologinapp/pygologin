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
});

print('profile id=', profile_id);

# gl.update({
#     "id": 'yU0Pr0f1leiD',
#     "name": 'profile_mac2',
# });

profile = gl.getProfile(profile_id);

print('new profile name=', profile.get("name"));

# gl.delete('yU0Pr0f1leiD')