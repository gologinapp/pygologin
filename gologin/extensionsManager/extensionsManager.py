import os
import requests
import urllib.request
import pathlib
import zipfile
from sys import platform

from ..http_client import make_request

HOMEDIR = pathlib.Path.home()
CHROME_EXT_DIR_NAME = 'chrome-extensions'
EXTENSIONS_PATH = os.path.join(HOMEDIR, '.gologin', 'extensions')
CHROME_EXTENSIONS_PATH = os.path.join(EXTENSIONS_PATH, CHROME_EXT_DIR_NAME)
USER_CHROME_EXTENSIONS_PATH = os.path.join(EXTENSIONS_PATH, 'user-extensions')
EXTENSION_URL = 'https://clients2.google.com/service/update2/crx?response=redirect&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc&prodversion=97.0.4692.71'


class ExtensionsManager():
    def downloadExt(self, ids = []):
        extUrl = EXTENSION_URL.replace('{ext_id}', ids)
        uploadedProfileMetadata = getExtMetadata(extUrl)

        reqPath = uploadedProfileMetadata['Location']
        extVer = getExtVersion(reqPath)
        ext = os.path.join(CHROME_EXTENSIONS_PATH, ids + '@' + extVer)

        if os.path.exists(ext):
            return extVer
        
        else:
            fileName = ids + '@' + extVer + '.crx'
            pathExt = os.path.join(CHROME_EXTENSIONS_PATH, fileName)
            urllib.request.urlretrieve(extUrl, pathExt)
            
            f = open(pathExt, 'rb')
            r = f.read()
            zipExt = crxToZip(r)
            f.close()

            archiveZipPath = os.path.join(CHROME_EXTENSIONS_PATH, ids + '@' + extVer + '.zip')
            archiveZip = open(archiveZipPath, 'wb')
            archiveZip.write(zipExt)
            archiveZip.close()

            os.remove(os.path.join(CHROME_EXTENSIONS_PATH, fileName))

            with zipfile.ZipFile(archiveZipPath,'r') as zfile:
                zfile.extractall(ext)

            os.remove(os.path.join(CHROME_EXTENSIONS_PATH, archiveZipPath))

            return extVer
    
    def downloadUserChromeExt(self, profile_id, extensions_to_download=[], access_token=''):
        if not os.path.exists(USER_CHROME_EXTENSIONS_PATH):
            os.makedirs(USER_CHROME_EXTENSIONS_PATH)
        existed_user_extensions = []
        for ext_id in extensions_to_download:
            ext_folder = os.path.join(USER_CHROME_EXTENSIONS_PATH, ext_id)

            if os.path.exists(ext_folder):
                existed_user_extensions.append(ext_id)
                continue
            
            request_data = {
                'existedUserChromeExtensions': existed_user_extensions,
                'profileId': profile_id,
                'userChromeExtensions': [ext_id]
            }

            headers = {
                'Authorization': 'Bearer ' + access_token,
                'User-Agent': 'Selenium-API'
            }
            
            response = make_request(
                'POST',
                f"https://api.gologin.com/extensions/user_chrome_extensions_paths",
                json_data=request_data,
                headers=headers
            )

            if response.status_code < 300:
                download_paths = response.json()

                for download_url in download_paths:
                    file_name = f"{ext_id}.zip"
                    zip_path = os.path.join(USER_CHROME_EXTENSIONS_PATH, file_name)
                    
                    urllib.request.urlretrieve(download_url, zip_path)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zip_file:
                        zip_file.extractall(ext_folder)
                    
                    os.remove(zip_path)


    def extensionIsAlreadyExisted(self, settings = {}, profileExtensionsCheck = []):
        extensionsSettings = settings['extensions']['settings']
        
        for p in profileExtensionsCheck:
            if platform == 'win32':
                p.replace('/', '\\')
                originalId = p.split('\\')[6].split('@')[0]
            else:
                originalId = p.split('/')[6].split('@')[0]

            if originalId in extensionsSettings:
                return True
            else:
                return False


def crxToZip(buf):
    isV3 = buf[4] == 3
    isV2 = buf[4] == 2

    if isV2:
        publicKeyLength = calcLength(buf[8], buf[9], buf[10], buf[11])
        signatureLength = calcLength(buf[12], buf[13], buf[14], buf[15])

        zipStartOffset = 16 + publicKeyLength + signatureLength

        return buf[zipStartOffset:]

    headerSize = calcLength(buf[8], buf[9], buf[10], buf[11])
    zipStartOffset = 12 + headerSize

    return buf[zipStartOffset:]


def calcLength(a, b, c, d):
    length = 0
    length += a << 0
    length += b << 8
    length += c << 16
    length += d << 24
    
    return length


def getExtMetadata(extUrl):
    x = requests.head(extUrl)
    
    return x.headers


def getExtVersion(metadata):
    extFullName = metadata.split('/')[6]
    splitExtName = extFullName.split('_', 1)[1]
    ver = splitExtName.split('.')[0]

    return ver
