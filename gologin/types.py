from typing import Dict, List, Literal, Optional, TypedDict, Union

OS = Literal['lin', 'mac', 'win', 'android']
T_OS_SPEC = Literal['M1', 'M2', 'M3', 'win11', '']

class CreateProfileRandomFingerprintOptions(TypedDict):
    os: OS
    name: str

class BookmarkChild(TypedDict):
    name: str
    url: str

class BookmarkFolder(TypedDict):
    name: str
    children: List[BookmarkChild]

IBookmarkFoldersObj = Dict[str, BookmarkFolder]

class NavigatorModel(TypedDict):
    userAgent: str
    resolution: str
    language: str
    platform: str
    hardwareConcurrency: int
    deviceMemory: int
    maxTouchPoints: Optional[int]

class TimezoneModel(TypedDict):
    enabled: bool
    fillBasedOnIp: bool
    timezone: str

class GeolocationModel(TypedDict):
    mode: Literal['prompt', 'block', 'allow']
    enabled: bool
    customize: bool
    fillBasedOnIp: bool
    latitude: float
    longitude: float
    accuracy: float

class AudioContextModel(TypedDict):
    enable: bool
    noiseValue: float

class CanvasModel(TypedDict):
    mode: Literal['off', 'noise']
    noise: Optional[float]

class FontsModel(TypedDict):
    enableMasking: bool
    enableDOMRect: bool
    families: List[str]

class MediaDevicesModel(TypedDict):
    enableMasking: bool
    videoInputs: int
    audioInputs: int
    audioOutputs: int

class WebRTCModel(TypedDict):
    mode: Literal['real', 'public']
    enabled: bool
    customize: bool
    localIpMasking: bool
    fillBasedOnIp: bool
    publicIp: str
    localIps: List[str]

class WebGlModel(TypedDict):
    mode: Literal['off', 'noise']
    getClientRectsNoise: float
    noise: Optional[float]

class ClientRectsModel(TypedDict):
    mode: Literal['off', 'noise']
    noise: float

class WebGlMetadataModel(TypedDict):
    mode: Literal['off', 'mask']
    vendor: str
    renderer: str

class BrowserProxyCreateValidation(TypedDict):
    mode: Literal['http', 'https', 'socks4', 'socks5', 'geolocation', 'none', 'tor', 'gologin']
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    changeIpUrl: Optional[str]
    autoProxyRegion: Optional[str]
    torProxyRegion: Optional[str]

class CreateCustomBrowserOptions(TypedDict, total=False):
    name: str
    notes: str
    autoLang: bool
    lockEnabled: bool
    folderName: str
    bookmarks: IBookmarkFoldersObj
    os: OS
    osSpec: T_OS_SPEC
    devicePixelRatio: float
    navigator: NavigatorModel
    proxy: BrowserProxyCreateValidation
    dns: str
    timezone: TimezoneModel
    geolocation: GeolocationModel
    audioContext: AudioContextModel
    canvas: CanvasModel
    fonts: FontsModel
    mediaDevices: MediaDevicesModel
    webRTC: WebRTCModel
    webGL: WebGlModel
    clientRects: ClientRectsModel
    webGLMetadata: WebGlMetadataModel
    chromeExtensions: List[str]
    userChromeExtensions: List[str]
    folders: List[str]

class Cookie(TypedDict, total=False):
    name: str
    value: str
    domain: str
    path: str
    expirationDate: Optional[float]
    creationDate: Optional[float]
    hostOnly: Optional[bool]
    httpOnly: Optional[bool]
    sameSite: Optional[Literal['no_restriction', 'lax', 'strict']]
    secure: Optional[bool]
    session: Optional[bool]
    url: Optional[str]
