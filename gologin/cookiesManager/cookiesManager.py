import sqlite3
import base64
from typing import List, Dict, Tuple
import datetime
import time
import os
from os import access, F_OK

MAX_SQLITE_VARIABLES = 1

SAME_SITE = {
    -1: 'unspecified',
    0: 'no_restriction',
    1: 'lax',
    2: 'strict',
}

COOKIE_ROW_COLUMN_NAMES = [
    'creation_utc',
    'host_key',
    'top_frame_site_key',
    'name',
    'value',
    'encrypted_value',
    'path',
    'expires_utc',
    'is_secure',
    'is_httponly',
    'last_access_utc',
    'has_expires',
    'is_persistent',
    'priority',
    'samesite',
    'source_scheme',
    'source_port',
    'last_update_utc',
]

class CookiesManager():
    def __init__(self, *args, **kwargs):
        self.profile_id = kwargs.get('profile_id')
        self.tmpdir = kwargs.get('tmpdir')

    def create_db_file(self, cookies_file_path, cookies_file_second_path=None, create_cookies_table_query=None):
        with open(cookies_file_path, 'w') as f:
            pass
        
        conn = sqlite3.connect(cookies_file_path)
        if create_cookies_table_query:
            conn.execute(create_cookies_table_query)
        conn.commit()
        conn.close()

        self._ensure_directory_exists(cookies_file_path)
        if cookies_file_second_path:
            self._ensure_directory_exists(cookies_file_second_path)
            try:
                with open(cookies_file_path, 'rb') as src_file:
                    with open(cookies_file_second_path, 'wb') as dst_file:
                        dst_file.write(src_file.read())
            except Exception as e:
                print(f'Error copying cookies file: {str(e)}')
    
    def _ensure_directory_exists(self, file_path):
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def get_db(self, file_path = None):
        if (not file_path):
            file_path = self.get_cookies_file_path()
        connection_opts = {"database": file_path}
        # print('FILEPATH', self.get_cookies_file_path())
        return sqlite3.connect(**connection_opts)

    def get_chunked_insert_values(self, cookies_arr: List[dict]) -> List[Tuple[str, List]]:
        today_unix = int(time.time())

        chunked_cookies_arr = [cookies_arr[i:i + MAX_SQLITE_VARIABLES] for i in range(0, len(cookies_arr), MAX_SQLITE_VARIABLES)]

        # for cookies in chunked_cookies_arr:
            # print('COOKIES::::::', cookies)
        result = []

        for cookies in chunked_cookies_arr:
            query_placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(cookies))
            query = f"insert or replace into cookies (creation_utc, host_key, top_frame_site_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, is_same_party, last_update_utc) values {query_placeholders}"

            query_params = []
            for cookie in cookies:
                creation_date = cookie.get("creationDate", self.unix_to_ldap(today_unix))
                expiration_date = 0 if cookie.get("session", False) else self.unix_to_ldap(cookie.get("expirationDate", 0))
                encrypted_value = cookie["value"]
                value = cookie["value"]
                samesite = next(key for key, value in SAME_SITE.items() if value == cookie.get("sameSite", "-1"))
                is_secure = 1 if cookie["name"].startswith("__Host-") or cookie["name"].startswith("__Secure-") else int(cookie.get("secure", 0))
                source_scheme = 2 if is_secure == 1 else 1
                source_port = 443 if is_secure == 1 else 80
                is_persistent = 0 if cookie.get("session") else 1 if expiration_date != 0 else 0

                if cookie.get("domain") == ".mail.google.com" and cookie["name"] == "COMPASS":
                    expiration_date = 0
                    is_persistent = 0

                query_params.append((
                    creation_date,
                    cookie.get("domain", ""),
                    "",
                    cookie["name"],
                    "",
                    cookie["value"],
                    cookie.get("path", ""),
                    expiration_date,
                    is_secure,
                    int(cookie.get("httpOnly", 0)),
                    0,
                    0 if expiration_date == 0 else 1,
                    is_persistent,
                    1,
                    samesite,
                    source_scheme,
                    source_port,
                    0,
                    0
                ))

            result.append((query, query_params))

        return result

    def load_cookies_from_file(self) -> List[Dict[str, any]]:
        db = None
        cookies = []

        try:
            db = self.get_db()
            cookies_rows = db.execute('select * from cookies')
            cookies_rows = cookies_rows.fetchall()
            for row in cookies_rows:
                row_data = dict(zip(COOKIE_ROW_COLUMN_NAMES, row))
                cookies.append({
                    'url': self.build_cookie_url(row_data['host_key'], row_data['is_secure'], row_data['path']),
                    'domain': row_data['host_key'],
                    'name': row_data['name'],
                    'value': row_data['encrypted_value'],
                    'path': row_data['path'],
                    'sameSite': SAME_SITE[row_data['samesite']],
                    'secure': bool(row_data['is_secure']),
                    'httpOnly': bool(row_data['is_httponly']),
                    'hostOnly': not row_data['host_key'].startswith('.'),
                    'session': not row_data['is_persistent'],
                    'expirationDate': self.ldap_to_unix(row_data['expires_utc']),
                    'creationDate': self.ldap_to_unix(row_data['creation_utc']),
                })
        except Exception as error:
            print('load_cookies_from_file', error)
            raise error
        finally:
            if db:
                db.close()

        return cookies

    def get_unique_cookies(self, cookies_arr: List[Dict[str, any]]) -> List[Dict[str, any]]:
        try:
            cookies_in_file = self.load_cookies_from_file()
            
            existing_cookie_names = set()
            for cookie in cookies_in_file:
                if isinstance(cookie['value'], bytes):
                    value_str = cookie['value'].decode('utf-8', errors='ignore')
                else:
                    value_str = str(cookie['value'])
                
                cookie_id = f"{cookie['name']}-{value_str}"
                existing_cookie_names.add(cookie_id)
            
            unique_cookies = []
            for cookie in cookies_arr:
                if isinstance(cookie['value'], bytes):
                    value_str = cookie['value'].decode('utf-8', errors='ignore')
                else:
                    value_str = str(cookie['value'])
                
                cookie_id = f"{cookie['name']}-{value_str}"
                if cookie_id not in existing_cookie_names:
                    unique_cookies.append(cookie)
            
            return unique_cookies
        except Exception as error:
            print('get_unique_cookies error:', error)
            return cookies_arr

    def unix_to_ldap(self, unixtime: int) -> int:
        if unixtime == 0:
            return unixtime
            
        win32_epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
        epoch_diff_seconds = (datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) - win32_epoch).total_seconds()
        
        windows_seconds = unixtime + epoch_diff_seconds
        ldap_timestamp = int(windows_seconds * 10000000)
        
        return ldap_timestamp

    def ldap_to_unix(self, ldap):
        ldap_str = str(int(ldap))  # Convert to integer first to avoid decimals
        ldap_length = len(ldap_str)

        if ldap == 0 or ldap_length > 18:
            return ldap

        _ldap = ldap
        if ldap_length < 18:
            _ldap = int(ldap_str + '0' * (18 - ldap_length))  # Padding zeros to the integer part

        # Create a datetime object for January 1, 1601
        win32_epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
        # Convert this to a Unix timestamp in milliseconds
        win32filetime_epoch = int(win32_epoch.timestamp() * 1000)

        return (_ldap / 10000 + win32filetime_epoch) / 1000

    def build_cookie_url(self, domain: str, secure: bool, path: str) -> str:
        domain_without_dot = domain[1:] if domain.startswith('.') else domain
        protocol = 'https://' if secure else 'http://'

        return protocol + domain_without_dot + path

    def chunk(self, arr: List, chunk_size: int = 1) -> List[List]:
        if chunk_size <= 0:
            return []

        return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

    def get_cookies_file_path(self) -> str:
        base_cookies_file_path = os.path.join(self.tmpdir, f'gologin_{self.profile_id}', 'Default', 'Cookies')
        bypass_cookies_file_path = os.path.join(self.tmpdir, f'gologin_{self.profile_id}', 'Default', 'Network', 'Cookies')

        if access(base_cookies_file_path, F_OK):
            return base_cookies_file_path

        if access(bypass_cookies_file_path, F_OK):
            return bypass_cookies_file_path

        return base_cookies_file_path


    def write_cookies_to_file(self, cookies, is_second_time = False, cookies_table_query = None):
        print ('write_cookies_to_file')

        result_cookies = []
        for cookie in cookies:
            buffer_data = cookie['value'].get('data', [])
            # print('buffer_data', buffer_data)
            cookie_value = bytes(buffer_data)
            # print('cookie_value', cookie_value)
            result_cookies.append({**cookie, 'value': cookie_value})

        base_cookies_file_path = os.path.join(self.tmpdir, f'gologin_{self.profile_id}', 'Default', 'Cookies')
        bypass_cookies_file_path = os.path.join(self.tmpdir, f'gologin_{self.profile_id}', 'Default', 'Network', 'Cookies')

        unique_cookies = self.get_unique_cookies(result_cookies)
        
        print('unique_cookies', unique_cookies)
        db = self.get_db(base_cookies_file_path)
        cursor = db.cursor()

        try:
            if len(unique_cookies) > 0:
                chunk_insert_values = self.get_chunked_insert_values(unique_cookies)
                for query, query_params in chunk_insert_values:
                    for params in query_params:
                        res = cursor.execute(query, params)
            db.commit()
            db.close()
        except Exception as error:
            print('write_cookies_to_file exception:', error, error.__traceback__.tb_lineno)
            if is_second_time:
                raise error
            else:
                try:
                    if os.path.exists(base_cookies_file_path):
                        os.remove(base_cookies_file_path)
                        print(f"Removed existing cookies file at {base_cookies_file_path}")
                except Exception as e:
                    print(f"Error removing cookies file: {str(e)}")
                self.create_db_file(base_cookies_file_path, bypass_cookies_file_path, cookies_table_query)
                self.write_cookies_to_file(cookies, True)
        finally:
            if db and unique_cookies:
                db.close()
                # Copy cookies file from base path to bypass path
                try:
                    self._ensure_directory_exists(bypass_cookies_file_path)
                    with open(base_cookies_file_path, 'rb') as src_file:
                        with open(bypass_cookies_file_path, 'wb') as dst_file:
                            dst_file.write(src_file.read())
                    print(f'Successfully copied cookies from {base_cookies_file_path} to {bypass_cookies_file_path}')
                except Exception as e:
                    print(f'Error copying cookies file: {str(e)}')
                