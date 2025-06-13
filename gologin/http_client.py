import requests
import logging

logger = logging.getLogger('gologin')

class HTTPClient:
    @staticmethod
    def make_request(
        method: str,
        url: str,
        headers: dict = None,
        json_data: dict = None,
        data=None,
        params: dict = None,
        proxies: dict = None,
        timeout: int = None
    ):
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_data,
                data=data,
                params=params,
                proxies=proxies,
                timeout=timeout
            )
            
            logger.debug(f"{method.upper()} {url} - Status: {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {method.upper()} {url} - Error: {e}")
            
            if "gologin.com" in url:
                retry_url = url.replace("gologin.com", "gologin.co")
                logger.info(f"Retrying request with alternative URL: {retry_url}")
                
                try:
                    response = requests.request(
                        method=method.upper(),
                        url=retry_url,
                        headers=headers,
                        json=json_data,
                        data=data,
                        params=params,
                        proxies=proxies,
                        timeout=timeout
                    )
                    logger.debug(f"{method.upper()} {retry_url} - Status: {response.status_code}")
                    return response
                    
                except requests.exceptions.RequestException as retry_e:
                    logger.error(f"Retry request also failed: {method.upper()} {retry_url} - Error: {retry_e}")
                    raise 'Proxy check failed. Please check your proxy or network connection'
            elif "geo.myip.link" in url:
                raise 'Proxy check failed. Please check your proxy or network connection'
            else:
                raise e

def make_request(
    method: str,
    url: str,
    headers: dict = None,
    json_data: dict = None,
    data=None,
    params: dict = None,
    proxies: dict = None,
    timeout: int = None
):
    return HTTPClient.make_request(
        method=method,
        url=url,
        headers=headers,
        json_data=json_data,
        data=data,
        params=params,
        proxies=proxies,
        timeout=timeout
    ) 