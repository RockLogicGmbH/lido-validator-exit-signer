"""
Validator class for specific config types.
FIXME: for whetever reason validators fail on macOS with errors like:
AttributeError: module 'validators' has no attribute 'ip_address'
"""
import socket
from typing import Optional, Union
import validators
from os.path import exists

class validate:

    @staticmethod
    def sv_addr(cls, addr: str) -> str:
        # if addr != "localhost" and not validators.domain(addr) and not validators.ip_address.ipv4(addr) and not validators.ip_address.ipv6(addr):
        #     raise ValueError(f"'SV_ADDR' must be a valid domain or IP, got: {addr}")
        try:
            socket.getaddrinfo(addr, None)
        except (socket.gaierror, UnicodeError):
            raise ValueError(f"'SV_ADDR' must be a valid domain or IP, got: {addr}")
        return addr

    @staticmethod
    def sv_port(cls, port: int) -> int:
        if not 1025 <= port <= 65535:
            raise ValueError(f"'SV_PORT' must be non-privileged, got: {port}")
        return port
    
    @staticmethod
    def sv_workers(cls, workers: Optional[Union[int, str]]) -> Optional[int]:
        if isinstance(workers, str) and workers.isnumeric():
            workers = int(workers)
        if workers is None or isinstance(workers, str) or workers < 2:
            return None
        if not 2 <= workers <= 1000:
            raise ValueError(f"'SV_WORKERS' must between 2 and 1000, None otherwise got: {workers}")
        return workers
    
    @staticmethod
    def sv_ssl_certfile(cls, certfile: str) -> str:
        if certfile and not exists(certfile):
            raise FileNotFoundError(f"'SV_SSL_CERTFILE' does not exist, got: {certfile}")
        return certfile
    
    @staticmethod
    def sv_ssl_keyfile(cls, keyfile: str) -> str:
        if keyfile and not exists(keyfile):
            raise FileNotFoundError(f"'SV_SSL_KEYFILE' does not exist, got: {keyfile}")
        return keyfile
    
    @staticmethod
    def sv_root_path(cls, root_path: str) -> str:
        # allow either empty root path or it must start with /
        if root_path and not root_path.startswith("/"):
            raise FileNotFoundError(f"'SV_ROOT_PATH' must either empty or start with a slash (/), got: {root_path}")
        return root_path
    

    

