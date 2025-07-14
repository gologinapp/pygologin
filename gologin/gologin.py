import json
import time
import os
import stat
import sys
import shutil
import requests
import zipfile
import subprocess
import pathlib
import tempfile
import socket
import random
import psutil
import logging
import sentry_sdk
from urllib.parse import quote

from .golgoin_types import CreateCustomBrowserOptions, CreateProfileRandomFingerprintOptions, BrowserProxyCreateValidation
from .http_client import make_request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gologin')
logger.setLevel(logging.INFO)  # Default to INFO level

from .extensionsManager import ExtensionsManager
from .cookiesManager import CookiesManager
from .browserManager import BrowserManager
from .zero_profile.preferences import zeroProfilePreferences
from .zero_profile.bookmarks import zeroProfileBookmarks
from ._version import __version__

API_URL = 'https://api.gologin.com'
PROFILES_URL = 'https://gprofiles-new.gologin.com/'
GET_TIMEZONE_URL = 'https://geo.myip.link'
FILES_GATEWAY = 'https://storage-worker-test.gologin.com'

class ProtocolException(Exception):
    def __init__(self, data:dict):
        self._json =data
        super().__init__(data.__repr__())
    @property
    def json(self) -> dict:
        return self._json

class GoLogin(object):
    def __init__(self, options):
        if (options.get('token') == 'Your token'):
            raise Exception('Token is required')
        if (options.get('profile_id') == 'Your profile id'):
            raise Exception('Profile ID is required')
        self.access_token = options.get('token')
        self.profile_id = options.get('profile_id')
        self.tmpdir = options.get('tmpdir', tempfile.gettempdir())
        self.address = options.get('address', '127.0.0.1')
        self.extra_params = options.get('extra_params', [])
        self.port = options.get('port', getRandomPort())
        self.local = options.get('local', False)
        self.spawn_browser = options.get('spawn_browser', True)
        self.credentials_enable_service = options.get(
            'credentials_enable_service')
        self.cleaningLocalCookies = options.get('cleaningLocalCookies', False)
        self.uploadCookiesToServer = options.get('uploadCookiesToServer', False)
        self.writeCookiesFromServer = options.get('writeCookiesFromServer', True)
        self.restore_last_session = options.get('restore_last_session', True)
        self.executablePath = options.get('executable_path', '')
        self.is_cloud_headless = options.get('is_cloud_headless', True)
        self.is_new_cloud_browser = options.get('is_new_cloud_browser', True)
        self.orbita_major_version = 0

        if (os.environ.get('DISABLE_TELEMETRY') != 'true'):
            def before_send(event, hint):
                ignored_errors = [
                    'Error posting to',
                    'Profile deleted or not found'
                ]
                if 'exc_info' in hint:
                    exc_type, exc_value, tb = hint['exc_info']
                    
                    package_error = False
                    current_tb = tb
                    while current_tb:
                        filename = current_tb.tb_frame.f_code.co_filename
                        print('filename', filename)
                        if 'gologin' in filename or 'pygologin' in filename:
                            package_error = True
                            break
                        current_tb = current_tb.tb_next
                    
                    if not package_error:
                        return None
                    
                    error_message = str(exc_value).lower()
                    if any(ignored_msg.lower() in error_message for ignored_msg in ignored_errors):
                        return None
                        
                return event
            
            sentry_sdk.init(
                dsn="https://afee3f3cafb8de3939880af171b037e1@sentry-new.amzn.pro/25",
                traces_sample_rate=1.0,
                release=__version__,
                before_send=before_send,
                default_integrations=False
            )

        if (options.get('debug')):
            logger.setLevel(logging.DEBUG)

        if self.extra_params:
            logger.debug('extra_params: %s', self.extra_params)
        self.setProfileId(options.get('profile_id'))
        self.preferences = {}
        self.pid = int()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()

    def setProfileId(self, profile_id):
        self.profile_id = profile_id
        if self.profile_id == None:
            return
        self.profile_path = os.path.join(
            self.tmpdir, 'gologin_' + self.profile_id)
        self.profile_default_folder_path = os.path.join(
            self.profile_path, 'Default')
        self.profile_zip_path = os.path.join(
            self.tmpdir, 'gologin_' + self.profile_id + '.zip')
        self.profile_zip_path_upload = os.path.join(
            self.tmpdir, 'gologin_' + self.profile_id+'_upload.zip')

    def loadExtensions(self):
        profile = self.profile
        chromeExtensions = profile.get('chromeExtensions')
        userChromeExtensions = profile.get('userChromeExtensions')
        extensionsManagerInst = ExtensionsManager()
        pathToExt = ''
        profileExtensionsCheck = []
        for ext in chromeExtensions:
            try:
                ver = extensionsManagerInst.downloadExt(ext)
                pathToExt += os.path.join(pathlib.Path.home(), '.gologin',
                                      'extensions', 'chrome-extensions', ext + '@' + ver + ',')
                profileExtensionsCheck.append(os.path.join(pathlib.Path.home(
                ), '.gologin', 'extensions', 'chrome-extensions', ext + '@' + ver))
            except Exception as e:
                continue
        for ext in userChromeExtensions:
            try:
                extensionsManagerInst.downloadUserChromeExt(self.profile_id, [ext], self.access_token)
                pathToExt += os.path.join(pathlib.Path.home(), '.gologin',
                                      'extensions', 'user-extensions', ext + ',')
                profileExtensionsCheck.append(os.path.join(pathlib.Path.home(
                ), '.gologin', 'extensions', 'user-extensions', ext))
            except Exception as e:
                continue

        pref_file = os.path.join(self.profile_path, 'Default', 'Preferences')
        with open(pref_file, 'r', encoding="utf-8") as pfile:
            preferences = json.load(pfile)

        noteExtExist = ExtensionsManager().extensionIsAlreadyExisted(
            preferences, profileExtensionsCheck)

        if noteExtExist:
            return
        else:
            return pathToExt

    def spawnBrowser(self):
        proxy = self.proxy
        proxy_host = ''
        if proxy:
            if proxy.get('mode') == None or proxy.get('mode') == 'geolocation':
                proxy['mode'] = 'http'
            proxy_host = proxy.get('host')
            proxy = self.formatProxyUrl(proxy)

        tz = self.tz.get('timezone')
        resolution = self.profile.get('navigator', {}).get('resolution', '1920x1080')
        screenWidth = int(resolution.split('x')[0])
        screenHeight = int(resolution.split('x')[1])
        params = [
            self.executablePath,
            '--remote-debugging-port='+str(self.port),
            '--password-store=basic',
            '--gologin-profile='+self.profile_name,
            '--lang=en-US',
            '--webrtc-ip-handling-policy=default_public_interface_only',
            '--disable-features=PrintCompositorLPAC',
            '--window-size='+str(screenWidth)+','+str(screenHeight),
            '--user-data-dir='+self.profile_path,
        ]

        chromeExtensions = self.profile.get('chromeExtensions')
        userChromeExtensions = self.profile.get('userChromeExtensions')
        if (chromeExtensions and len(chromeExtensions) > 0) or (userChromeExtensions and len(userChromeExtensions) > 0):
            paths = self.loadExtensions()
            if paths is not None:
                extToParams = '--load-extension=' + paths
                params.append(extToParams)

        if proxy:
            hr_rules = 'MAP * 0.0.0.0 , EXCLUDE %s' % (proxy_host)
            params.append('--host-resolver-rules='+hr_rules)
        
        if proxy and self.orbita_major_version < 135:
            params.append('--proxy-server='+proxy)

        if self.restore_last_session:
            params.append('--restore-last-session')

        for param in self.extra_params:
            params.append(param)

        if sys.platform == "darwin":
            open_browser = subprocess.Popen(params)
            self.pid = open_browser.pid
        else:
            open_browser = subprocess.Popen(params, start_new_session=True)
            self.pid = open_browser.pid

        try_count = 1
        url = str(self.address) + ':' + str(self.port)
        while try_count < 100:
            try:
                data = requests.get('http://'+url+'/json').content
                break
            except:
                try_count += 1
                time.sleep(1)
        return url

    def start(self):
        try:
            profile_path = self.createStartup()
            if self.spawn_browser == True:
                return self.spawnBrowser()
            return profile_path
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise e
    
    def get_chromium_version(self):
        return self.chromium_version

    def zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                if not os.path.exists(path):
                    continue
                if stat.S_ISSOCK(os.stat(path).st_mode):
                    continue
                ziph.write(path, path.replace(self.profile_path, ''))

    def waitUntilProfileUsing(self, try_count=0):
        if try_count > 10:
            return
        time.sleep(1)
        profile_path = self.profile_path
        if os.path.exists(profile_path):
            try:
                os.rename(profile_path, profile_path)
            except OSError as e:
                logger.debug("waiting chrome termination")
                self.waitUntilProfileUsing(try_count+1)

    def stop(self):
        for proc in psutil.process_iter(['pid']):
            if proc.info.get('pid') == self.pid:
                proc.kill()
        self.waitUntilProfileUsing()
        self.sanitizeProfile()
        if self.local == False:
            self.commitProfile()
            os.remove(self.profile_zip_path_upload)
            shutil.rmtree(self.profile_path)
        print('profile stopped')

    def commitProfile(self):
        logger.debug('commitProfile')
        zipf = zipfile.ZipFile(
            self.profile_zip_path_upload, 'w', zipfile.ZIP_DEFLATED)
        self.zipdir(self.profile_default_folder_path, zipf)
        zipf.writestr('First Run', '')
        zipf.close()

        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API',
            'Content-Type': 'application/zip',
            'browserId': self.profile_id
        }

        response = make_request('PUT', FILES_GATEWAY + '/upload', headers=headers, data=open(self.profile_zip_path_upload, 'rb'))
        logger.debug('commitProfile completed: %s', response)


    def commitProfileOld(self):
        zipf = zipfile.ZipFile(
            self.profile_zip_path_upload, 'w', zipfile.ZIP_DEFLATED)
        self.zipdir(self.profile_path, zipf)
        zipf.close()

        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }

        response = make_request('GET', API_URL + '/browser/' + self.profile_id + '/storage-signature', headers=headers)
        signedUrl = response.content.decode('utf-8')

        make_request('PUT', signedUrl, data=open(self.profile_zip_path_upload, 'rb'))

        # print('commit profile complete')

    def sanitizeProfile(self):
        if (self.cleaningLocalCookies):
            path_to_coockies = os.path.join(
                self.profile_path, 'Default', 'Network', 'Cookies')
            os.remove(path_to_coockies)

        SEPARATOR = os.sep

        remove_dirs = [
            f"Default{SEPARATOR}Cache",
            f"Default{SEPARATOR}Service Worker",
            f"Default{SEPARATOR}Code Cache",
            f"Default{SEPARATOR}GPUCache",
            f"Default{SEPARATOR}Service Worker",
            f"Default{SEPARATOR}Extensions",
            f"Default{SEPARATOR}IndexedDB",
            f"Default{SEPARATOR}GPUCache",
            f"Default{SEPARATOR}DawnCache",
            f"Default{SEPARATOR}fonts_config",
            f"GrShaderCache",
            f"ShaderCache",
            f"biahpgbdmdkfgndcmfiipgcebobojjkp",
            f"afalakplffnnnlkncjhbmahjfjhmlkal",
            f"cffkpbalmllkdoenhmdmpbkajipdjfam",
            f"Dictionaries",
            f"enkheaiicpeffbfgjiklngbpkilnbkoi",
            f"oofiananboodjbbmdelgdommihjbkfag",
            f"SafetyTips",
            f"fonts",
        ]

        for d in remove_dirs:
            fpath = os.path.join(self.profile_path, d)
            if os.path.exists(fpath):
                try:
                    shutil.rmtree(fpath)
                except:
                    continue

    def formatProxyUrl(self, proxy):
        return proxy.get('mode', 'http')+'://'+proxy.get('host', '')+':'+str(proxy.get('port', 80))

    def formatProxyUrlPassword(self, proxy):
        mode = "socks5h" if proxy.get(
            "mode") == "socks5" else proxy.get("mode", "http")
        if proxy.get('username', '') == '':
            return mode+'://'+proxy.get('host', '')+':'+str(proxy.get('port', 80))
        else:
            return mode+'://'+quote(proxy.get('username', ''), safe='')+':'+quote(proxy.get('password', ''), safe='')+'@'+proxy.get('host', '')+':'+str(proxy.get('port', 80))

    def getTimeZone(self):
        proxy = self.proxy
        if proxy:
            proxies = {
                'http': self.formatProxyUrlPassword(proxy),
                'https': self.formatProxyUrlPassword(proxy)
            }
            response = make_request('GET', GET_TIMEZONE_URL, proxies=proxies)
        else:
            response = make_request('GET', GET_TIMEZONE_URL)
        return json.loads(response.content.decode('utf-8'))

    def getProfile(self, profile_id=None):
        profile = self.profile_id if profile_id == None else profile_id
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }
        response = make_request('GET', API_URL + '/browser/features/' + profile + '/info-for-run', headers=headers)
        data = json.loads(response.content.decode('utf-8'))

        if data.get("statusCode") == 404:
            raise Exception(data.get("error") + ": " + data.get("message"))
        return data

    def downloadProfileZip(self):
        logger.debug("downloadProfileZip")
        s3path = self.profile.get('s3Path', '')
        logger.debug('s3path: %s', s3path)
        data = ''
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API',
            'browserId': self.profile_id
        }

        response = make_request('GET', FILES_GATEWAY + '/download', headers=headers)
        data = response.content

        with open(self.profile_zip_path, 'wb') as f:
                f.write(data)


        self.extractProfileZip()

        # if not os.path.exists(os.path.join(self.profile_path, 'Default', 'Preferences')):
        #     print('preferences not found - creating fresh profile content')
        #     self.uploadEmptyProfile()
        #     self.createEmptyProfile()
        #     self.extractProfileZip()

    def createEmptyProfile(self):
        logger.debug('createEmptyProfile')
        default_path = os.path.join(self.profile_path, 'Default')
        network_path = os.path.join(default_path, 'Network')
        
        os.makedirs(network_path, exist_ok=True)
        
        preferences_file_path = os.path.join(default_path, 'Preferences')
        bookmarks_file_path = os.path.join(default_path, 'Bookmarks')
        cookies_file_path = os.path.join(network_path, 'Cookies')
        cookies_file_second_path = os.path.join(default_path, 'Cookies')
        
        create_cookies_table_query = self.profile.get('createCookiesTableQuery')
        
        with open(preferences_file_path, 'w') as f:
            json.dump(zeroProfilePreferences, f)
        
        with open(bookmarks_file_path, 'w') as f:
            json.dump(zeroProfileBookmarks, f)

        cookiesManagerInst = CookiesManager(
            profile_id=self.profile_id,
            tmpdir=self.tmpdir
        )
        
        cookiesManagerInst.create_db_file(
            cookies_file_path=cookies_file_path,
            cookies_file_second_path=cookies_file_second_path,
            create_cookies_table_query=create_cookies_table_query
        )

    def extractProfileZip(self):

        with zipfile.ZipFile(self.profile_zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.profile_path)
        logger.debug('profile extracted: %s', self.profile_path)
        os.remove(self.profile_zip_path)

    def getGeolocationParams(self, profileGeolocationParams, tzGeolocationParams):
        if profileGeolocationParams.get('fillBasedOnIp'):
            return {
                'mode': profileGeolocationParams['mode'],
                'latitude': float(tzGeolocationParams['latitude']),
                'longitude': float(tzGeolocationParams['longitude']),
                'accuracy': float(tzGeolocationParams['accuracy']),
            }

        return {
            'mode': profileGeolocationParams['mode'],
            'latitude': profileGeolocationParams['latitude'],
            'longitude': profileGeolocationParams['longitude'],
            'accuracy': profileGeolocationParams['accuracy'],
        }

    def getGologinPreferences(self, profileData):
        os = profileData.get('os', '')
        osSpec = profileData.get('osSpec', '')
        isM1 = profileData.get('isM1', False)
        isArm = (os == 'mac' and osSpec and 'M' in osSpec) or isM1
        resolution = profileData.get('navigator', {}).get('resolution', '1920x1080')
        screenWidth = int(resolution.split('x')[0])
        screenHeight = int(resolution.split('x')[1])
        langHeader = profileData.get('navigator', {}).get('language', '')
        logger.debug('langHeader: %s', langHeader)
        splittedLangs = langHeader.split(',')[0] if langHeader else 'en-US'

        startupUrl = profileData.get('startUrl', '').strip().split(',')[0]
        startupUrls = [url.strip() for url in profileData.get('startUrl', '').split(',') if url.strip()]
        self.tz = self.getTimeZone()

        if self.proxy and self.proxy.get('id'):
            status_body = {
                'proxies': [
                    {
                        'id': self.proxy.get('id'),
                        'status': True,
                        'country': self.tz.get('country'),
                        'city': self.tz.get('city'),
                        'lastIp': self.tz.get('ip'),
                        'timezone': self.tz.get('timezone'),
                        'checkDate': int(time.time())
                    }
                ]
            }
            print(status_body)
            try:
                make_request(
                    'POST',
                    f"{API_URL}/proxy/set_proxy_statuses",
                    headers={'Authorization': f'Bearer {self.access_token}'},
                    json_data=status_body,
                    timeout=13
                )
            except Exception as e:
                print(e)

        preferences = {
            'profile_id': profileData.get('id'),
            'name': profileData.get('name'),
            'is_m1': isArm,
            'geolocation': profileData.get('geolocation', {}),
            'navigator': {
                'platform': profileData.get('navigator', {}).get('platform', ''),
                'max_touch_points': profileData.get('navigator', {}).get('maxTouchPoints', 0),
            },
            'dns': profileData.get('dns', {}),
            'proxy': {
                'username': profileData.get('proxy', {}).get('username', ''),
                'password': profileData.get('proxy', {}).get('password', ''),
            },
            'webRTC': profileData.get('webRTC', {}),
            'screenHeight': screenHeight,
            'screenWidth': screenWidth,
            'userAgent': profileData.get('navigator', {}).get('userAgent', ''),
            'webGl': {
                'vendor': profileData.get('webGLMetadata', {}).get('vendor', ''),
                'renderer': profileData.get('webGLMetadata', {}).get('renderer', ''),
                'mode': profileData.get('webGLMetadata', {}).get('mode', '') == 'mask',
            },
            'webRTC': profileData.get('webRTC', {}),
            'webgl': {
                'metadata': {
                    'vendor': profileData.get('webGLMetadata', {}).get('vendor', ''),
                    'renderer': profileData.get('webGLMetadata', {}).get('renderer', ''),
                    'mode': profileData.get('webGLMetadata', {}).get('mode', '') == 'mask',
                },
            },
            'mobile': {
                'enable': profileData.get('os', False) == 'android',
                'width': profileData.get('screenWidth', 1920),
                'height': profileData.get('screenHeight', 1080),
                'device_scale_factor': profileData.get('devicePixelRatio', 1),
            },
            'webglParams': profileData.get('webglParams', {}),
            'webGpu': profileData.get('webGpu', {}),
            'webgl_noice_enable': profileData.get('webGL', {}).get('mode') == 'noise',
            'webglNoiceEnable': profileData.get('webGL', {}).get('mode') == 'noise',
            'webgl_noise_enable': profileData.get('webGL', {}).get('mode') == 'noise',
            'webgl_noise_value': profileData.get('webGL', {}).get('noise'),
            'webglNoiseValue': profileData.get('webGL', {}).get('noise'),
            'getClientRectsNoice': profileData.get('clientRects', {}).get('noise') or profileData.get('webGL', {}).get('getClientRectsNoise'),
            'client_rects_noise_enable': profileData.get('clientRects', {}).get('mode') == 'noise',
            'media_devices': {
                'enable': profileData.get('mediaDevices', {}).get('enableMasking', True),
                'uid': profileData.get('mediaDevices', {}).get('uid', ''),
                'audioInputs': profileData.get('mediaDevices', {}).get('audioInputs', 1),
                'audioOutputs': profileData.get('mediaDevices', {}).get('audioOutputs', 1),
                'videoInputs': profileData.get('mediaDevices', {}).get('videoInputs', 1),
            },
            'doNotTrack': profileData.get('navigator', {}).get('doNotTrack', False),
            'plugins': {
                'all_enable': profileData.get('plugins', {}).get('enableVulnerable', True),
                'flash_enable': profileData.get('plugins', {}).get('enableFlash', True),
            },
            'storage': {
                'enable': profileData.get('storage', {}).get('local', True),
            },
            'audioContext': {
                'enable': profileData.get('audioContext', {}).get('mode', 'off') != 'off',
                'noiseValue': profileData.get('audioContext', {}).get('noise', ''),
            },
            'canvas': {
                'mode': profileData.get('canvas', {}).get('mode', ''),
            },
            'languages': splittedLangs,
            'langHeader': langHeader,
            'canvasMode': profileData.get('canvas', {}).get('mode', ''),
            'canvasNoise': profileData.get('canvas', {}).get('noise', ''),
            'deviceMemory': profileData.get('navigator', {}).get('deviceMemory', 0),
            'hardwareConcurrency': profileData.get('navigator', {}).get('hardwareConcurrency', 2),
            'deviceMemory': profileData.get('navigator', {}).get('deviceMemory', 2) * 1024,
            'startupUrl': startupUrl,
            'startup_urls': startupUrls,
            'geolocation': {
                'mode': profileData.get('geolocation', {}).get('mode', 'prompt'),
                'latitude': float(self.tz.get('ll', [0, 0])[0]),
                'longitude': float(self.tz.get('ll', [0, 0])[1]),
                'accuracy': float(self.tz.get('accuracy', 0)),
            },
            'timezone': {
                'id': self.tz.get('timezone', ''),
            },
        }

        if self.orbita_major_version >= 135 and profileData.get('proxy', { 'mode': 'none'}).get('mode') != 'none':
            serverString = profileData.get('proxy').get('mode') + '://'
            if (profileData.get('proxy').get('username')):
                serverString += quote(profileData.get('proxy').get('username'), safe='')
            if (profileData.get('proxy').get('password')):
                serverString += ':' + quote(profileData.get('proxy').get('password'), safe='')
            serverString += '@' + profileData.get('proxy').get('host') + ':' + str(profileData.get('proxy').get('port'))

            preferences['proxy'] = {
                'mode': 'fixed_servers',
                'schema': profileData.get('proxy').get('mode'),
                'username': quote(profileData.get('proxy').get('username'), safe=''),
                'password': quote(profileData.get('proxy').get('password'), safe=''),
                'server': serverString
            }

        self.preferences = preferences

        return preferences

    def updatePreferences(self):
        pref_file = os.path.join(self.profile_path, 'Default', 'Preferences')

        if not os.path.exists(pref_file):
            os.makedirs(os.path.dirname(pref_file), exist_ok=True)
            with open(pref_file, 'w') as pfile:
                json.dump(zeroProfilePreferences, pfile)

        with open(pref_file, 'r', encoding="utf-8") as pfile:
            preferences = json.load(pfile)
        profile = self.profile
        profile['profile_id'] = self.profile_id

        proxy = self.profile.get('proxy')
        if proxy and (proxy.get('mode') == 'gologin' or proxy.get('mode') == 'tor'):
            autoProxyServer = profile.get('autoProxyServer')
            splittedAutoProxyServer = autoProxyServer.split('://')
            splittedProxyAddress = splittedAutoProxyServer[1].split(':')
            port = splittedProxyAddress[1]

            proxy = {
                'mode': 'http',
                'host': splittedProxyAddress[0],
                'port': port,
                'username': profile.get('autoProxyUsername'),
                'password': profile.get('autoProxyPassword'),
                'timezone': profile.get('autoProxyTimezone', 'us'),
            }

            profile['proxy']['username'] = profile.get('autoProxyUsername')
            profile['proxy']['password'] = profile.get('autoProxyPassword')

        if not proxy or proxy.get('mode') == 'none':
            logger.debug('no proxy')
            proxy = None

        if proxy and proxy.get('mode') == 'geolocation':
            proxy['mode'] = 'http'

        if proxy and proxy.get('mode') == None:
            proxy['mode'] = 'http'

        self.proxy = proxy
        self.profile_name = profile.get('name')
        if self.profile_name == None:
            print('empty profile name')
            print('profile=', profile)
            exit()

        gologin = self.getGologinPreferences(profile)

        if (gologin.get('proxy', {}).get('mode') == 'fixed_servers'):
            preferences['proxy'] = {
                'mode': 'fixed_servers',
                'server': gologin.get('proxy').get('server')
            }

        if self.credentials_enable_service != None:
            preferences['credentials_enable_service'] = self.credentials_enable_service
        preferences['gologin'] = gologin
        with open(pref_file, 'w') as pfile:
            # print('preferences', preferences)
            json.dump(preferences, pfile)

    def createStartup(self):
        logger.debug('createStartup: %s', self.profile_path)
        if self.local == False and os.path.exists(self.profile_path):
            try:
                shutil.rmtree(self.profile_path)
            except:
                logger.debug("error removing profile: %s", self.profile_path)
        self.profile = self.getProfile()

        if (self.executablePath == ''):
            uaVersion = self.profile.get('navigator', {}).get('userAgent', '')

            # Extract the full Chrome version from the user agent string
            chrome_version_part = uaVersion.split('Chrome/')[1].split(' ')[0] if 'Chrome/' in uaVersion else ''
            browserMajorVersion = chrome_version_part.split('.')[0] if chrome_version_part else ''
            self.orbita_major_version = int(browserMajorVersion)
            logger.debug('browserMajorVersion: %s', browserMajorVersion)
            logger.debug('chrome_version_part: %s', chrome_version_part)
            # Get the full version like 132.1.2.73
            self.chromium_version = chrome_version_part
            browser_manager = BrowserManager()

            self.executablePath = browser_manager.get_orbita_path(browserMajorVersion)

        isNewProfile = self.profile.get('storageInfo', {}).get('isNewProfile', False)
        if self.local == False and not isNewProfile:
            self.downloadProfileZip()
        if self.local == False and isNewProfile:
            self.createEmptyProfile()
        self.updatePreferences()

        if self.writeCookiesFromServer and self.profile.get('cookies').get('userCookies'):
            self.downloadCookies()
            print('cookies downloaded')
        return self.profile_path

    def downloadCookies(self):
        api_base_url = API_URL

        cookiesManagerInst = CookiesManager(
            profile_id = self.profile_id,
            tmpdir = self.tmpdir
        )

        cookies_table_query = self.profile.get('createCookiesTableQuery')
        cookiesData = self.profile.get('cookies')
        cookies = cookiesData.get('cookies')

        try:
            cookiesManagerInst.write_cookies_to_file(cookies, False, cookies_table_query)
        except Exception as e:
            logger.debug('downloadCookies exception: %s, line: %s', e, e.__traceback__.tb_lineno)
            raise e


    def uploadCookies(self, cookies):
        api_base_url = API_URL
        access_token = self.access_token

        try:
            response = make_request(
                'POST',
                f"{api_base_url}/browser/{self.profile_id}/cookies/?encrypted=true",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'User-Agent': 'Selenium-API'
                },
                json_data=cookies
            )
            return response
        except Exception as e:
            logger.debug('uploadCookies error: %s', e)
            return e

    def headers(self):
        return {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }

    def waitDebuggingUrl(self, delay_s, remote_orbita_url, try_count=3):
        url = remote_orbita_url + '/json/version'
        wsUrl = ''
        try_number = 1
        while wsUrl == '':
            time.sleep(delay_s)
            try:
                response = json.loads(requests.get(url).content)
                wsUrl = response.get('webSocketDebuggerUrl', '')
            except:
                pass
            if try_number >= try_count:
                return {'status': 'failure', 'wsUrl': wsUrl}
            try_number += 1

        remote_orbita_url_without_protocol = remote_orbita_url.replace(
            'https://', '')
        wsUrl = wsUrl.replace(
            'ws://', 'wss://').replace('127.0.0.1', remote_orbita_url_without_protocol)
        print('wsUrl', wsUrl)
        return {'status': 'success', 'wsUrl': wsUrl}

    def startRemote(self, delay_s=3):
        http_response = make_request(
            'POST',
            API_URL + '/browser/' + self.profile_id + '/web',
            headers=self.headers(),
            json_data={'isNewCloudBrowser': self.is_new_cloud_browser, 'isHeadless': self.is_cloud_headless}
        )
        responseJson = http_response.content.decode('utf-8')
        response = json.loads(responseJson)
        logger.debug('profileResponse: %s', response)

        remote_orbita_url = 'https://' + self.profile_id + '.orbita.gologin.com'
        if self.is_new_cloud_browser:
            if not response['remoteOrbitaUrl']:
                raise Exception('Couldn\' start the remote browser')
            remote_orbita_url = response['remoteOrbitaUrl']

        return self.waitDebuggingUrl(delay_s, remote_orbita_url=remote_orbita_url)

    def stopRemote(self):
        response = make_request(
            'DELETE',
            API_URL + '/browser/' + self.profile_id + '/web',
            headers=self.headers(),
            params={'isNewCloudBrowser': self.is_new_cloud_browser}
        )

    def clearCookies(self, profile_id=None):
        self.cleaningLocalCookies = True

        profile = self.profile_id if profile_id == None else profile_id
        resp = make_request(
            'POST',
            API_URL + '/browser/' + profile + '/cookies?cleanCookies=true',
            headers=self.headers(),
            json_data=[]
        )

        if resp.status_code == 204:
            return {'status': 'success'}
        else:
            return {'status': 'failure'}

    async def normalizePageView(self, page):
        if self.preferences.get("screenWidth") == None:
            self.profile = self.getProfile()
            self.preferences['screenWidth'] = int(self.profile.get(
                "navigator").get("resolution").split('x')[0])
            self.preferences['screenHeight'] = int(
                self.profile.get("navigator").get("resolution").split('x')[1])
        width = self.preferences.get("screenWidth")
        height = self.preferences.get("screenHeight")
        await page.setViewport({"width": width, "height": height})
    
    # api for managing profiles
    def getRandomFingerprint(self, options: dict = {}):
        os_type = options.get('os', 'lin')
        print(API_URL + '/browser/fingerprint?os=' + os_type)
        response = make_request('GET', API_URL + '/browser/fingerprint?os=' + os_type, headers=self.headers())
        return json.loads(response.content.decode('utf-8'))

    def profiles(self):
        response = make_request('GET', API_URL + '/browser/v2', headers=self.headers())
        return json.loads(response.content.decode('utf-8'))

    def create(self, options={}):
        profile_options = self.getRandomFingerprint(options)
        navigator = options.get('navigator')
        if options.get('navigator'):
            resolution = navigator.get('resolution')
            userAgent = navigator.get('userAgent')
            language = navigator.get('language')
            hardwareConcurrency = navigator.get('hardwareConcurrency')
            deviceMemory = navigator.get('deviceMemory')

            if resolution == 'random' or userAgent == 'random':
                options.pop('navigator')
            if resolution != 'random' and userAgent != 'random':
                options.pop('navigator')
            if resolution == 'random' and userAgent != 'random':
                profile_options['navigator']['userAgent'] = userAgent
            if userAgent == 'random' and resolution != 'random':
                profile_options['navigator']['resolution'] = resolution
            if resolution != 'random' and userAgent != 'random':
                profile_options['navigator']['userAgent'] = userAgent
                profile_options['navigator']['resolution'] = resolution
            if hardwareConcurrency != 'random' and userAgent != 'random' and hardwareConcurrency != None:
                profile_options['navigator']['hardwareConcurrency'] = hardwareConcurrency
            if deviceMemory != 'random' and userAgent != 'random' and deviceMemory != None:
                profile_options['navigator']['deviceMemory'] = deviceMemory

            profile_options['navigator']['language'] = language

        profile = {
            "name": "default_name",
            "notes": "auto generated",
            "browserType": "chrome",
            "os": "lin",
            "googleServicesEnabled": True,
            "lockEnabled": False,
            "audioContext": {
                "mode": "noise"
            },
            "canvas": {
                "mode": "noise"
            },
            "webRTC": {
                "mode": "disabled",
                "enabled": False,
                "customize": True,
                "fillBasedOnIp": True
            },
            "fonts": {
                "families": profile_options.get('fonts')
            },
            "navigator": profile_options.get('navigator', {}),
            "profile": json.dumps(profile_options),
        }

        if options.get('storage'):
            profile['storage'] = options.get('storage')

        for k, v in options.items():
            profile[k] = v

        http_response = make_request('POST', API_URL + '/browser', headers=self.headers(), json_data=profile)
        response = json.loads(http_response.content.decode('utf-8'))
        if not (response.get('statusCode') is None):
            raise ProtocolException(response)
        return response.get('id')

    def delete(self, profile_id=None):
        profile = self.profile_id if profile_id == None else profile_id
        make_request('DELETE', API_URL + '/browser/' + profile, headers=self.headers())

    def update(self, options):
        self.profile_id = options.get('id')
        profile = self.getProfile()
        # print("profile", profile)
        for k, v in options.items():
            profile[k] = v
        resp = make_request('PUT', API_URL + '/browser/' + self.profile_id, headers=self.headers(), json_data=profile)
        resp_content = resp.content.decode('utf-8')

    def createProfileWithCustomParams(self, options: CreateCustomBrowserOptions):
        """Create a profile with custom parameters"""
        response = make_request(
            'POST',
            f"{API_URL}/browser/custom",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
            },
            json_data=options
        )

        if response.status_code == 400:
            data = response.json()
            raise Exception(f"gologin failed account creation with status code, {response.status_code} DATA {json.dumps(data)}")

        if response.status_code == 500:
            raise Exception(f"gologin failed account creation with status code, {response.status_code}")

        profile = response.json()
        return profile.get('id')

    def refreshProfilesFingerprint(self, profileIds: list[str]):
        if not profileIds:
            raise Exception('Profile ID is required')

        response = make_request(
            'PATCH',
            f"{API_URL}/browser/fingerprints",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data={"browsersIds": profileIds}
        )

        return response.json()

    def createProfileRandomFingerprint(self, options: CreateProfileRandomFingerprintOptions):
        if options is None:
            options = {}
            
        os_type = options.get('os', 'lin')
        name = options.get('name', 'api-generated')

        response = make_request(
            'POST',
            f"{API_URL}/browser/quick",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data={
                "os": os_type,
                "osSpec": options.get('osSpec', ''),
                "name": name,
            }
        )

        return response.json()

    def updateUserAgentToLatestBrowser(self, profileIds, workspaceId=''):
        """Update user agent to latest browser version"""
        url = f"{API_URL}/browser/update_ua_to_new_browser_v"
        if workspaceId:
            url += f"?currentWorkspace={workspaceId}"

        response = make_request(
            'PATCH',
            url,
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data={
                "browserIds": profileIds,
                "updateUaToNewBrowserV": True,
                "updateAllProfiles": False,
                "testOrbita": False
            }
        )

        return response.json()

    def changeProfileProxy(self, profileId: str, proxyData: BrowserProxyCreateValidation):
        """Change proxy settings for a profile"""
        logger.debug(f"Changing proxy for profile {profileId}: {proxyData}")
        response = make_request(
            'PATCH',
            f"{API_URL}/browser/{profileId}/proxy",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data=proxyData
        )

        return response.status_code

    def getAvailableType(self, availableTrafficData):
        """Determine available proxy type based on traffic data"""
        if availableTrafficData['mobileTrafficData']['trafficUsedBytes'] > availableTrafficData['mobileTrafficData']['trafficLimitBytes']:
            return 'mobile'
        elif availableTrafficData['residentialTrafficData']['trafficUsedBytes'] < availableTrafficData['residentialTrafficData']['trafficLimitBytes']:
            return 'resident'
        elif availableTrafficData['dataCenterTrafficData']['trafficUsedBytes'] < availableTrafficData['dataCenterTrafficData']['trafficLimitBytes']:
            return 'dataCenter'
        else:
            return 'none'

    def addGologinProxyToProfile(self, profileId, countryCode, proxyType=''):
        """Add Gologin proxy to a profile"""
        trafficLimitMessage = "Traffic limit exceeded"
        
        if not proxyType:
            availableTraffic = make_request(
                'GET',
                f"{API_URL}/users-proxies/geolocation/traffic",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'User-Agent': 'gologin-api',
                    'Content-Type': 'application/json',
                }
            )

            availableTrafficData = availableTraffic.json()
            logger.debug(f"Available traffic data: {availableTrafficData}")
            availableType = self.getAvailableType(availableTrafficData)
            if availableType == 'none':
                raise Exception(trafficLimitMessage)

            logger.debug(f"Available proxy type: {availableType}")
            proxyType = availableType

        isDc = False
        isMobile = False

        if proxyType == 'mobile':
            isMobile = True
            isDc = False
        elif proxyType == 'resident':
            isMobile = False
            isDc = False
        elif proxyType == 'dataCenter':
            isMobile = False
            isDc = True
        else:
            raise Exception('Invalid proxy type')

        proxyResponse = make_request(
            'POST',
            f"{API_URL}/users-proxies/mobile-proxy",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data={
                "countryCode": countryCode,
                "isDc": isDc,
                "isMobile": isMobile,
                "profileIdToLink": profileId,
            }
        )

        proxy = proxyResponse.json()
        if proxy.get('trafficLimitBytes', 0) < proxy.get('trafficUsedBytes', 0):
            raise Exception(trafficLimitMessage)

        return proxy

    def addCookiesToProfile(self, profileId, cookies):
        """Add cookies to a profile"""
        response = make_request(
            'POST',
            f"{API_URL}/browser/{profileId}/cookies?fromUser=true",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': 'gologin-api',
                'Content-Type': 'application/json',
            },
            json_data=cookies
        )

        return response.status_code


def getRandomPort():
    while True:
        port = random.randint(1000, 35000)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            continue
        else:
            return port
        sock.close()
