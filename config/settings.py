import platform
import sys
from typing import Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from .validate import validate

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=('../.env', '.env', '../.env.dev', '.env.dev'),
        env_file_encoding="utf-8",
        #env_prefix='EXSI_',
        extra="ignore", # https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra
    )

    #
    # DEV
    #

    AUTORELOAD: bool = True

    #
    # UI SERVER
    #

    # The ip address or domain the ui accepts connections on
    SV_ADDR: str = "0.0.0.0"
    @field_validator("SV_ADDR")
    def check_sv_addr(cls, addr: str) -> str:
        return validate.sv_addr(cls,addr)
    
    # The port the ui accepts connections on
    SV_PORT: int = 7524
    @field_validator("SV_PORT")
    def check_sv_port(cls, port: int) -> int:
        return validate.sv_port(cls,port)
    
    # Number of workers for the backend server or string 'None'
    SV_WORKERS: Optional[Union[int, str]] = None
    @field_validator("SV_WORKERS")
    def check_sv_workers(cls, workers: Optional[Union[int,str]]) -> Optional[int]:
        return validate.sv_workers(cls,workers)
    
    # SSL cert file
    SV_SSL_CERTFILE: str = ""
    @field_validator("SV_SSL_CERTFILE")
    def check_sv_ssl_certfile(cls, certfile: str) -> int:
        return validate.sv_ssl_certfile(cls,certfile)
    
    # SSL key file
    SV_SSL_KEYFILE: str = ""
    @field_validator("SV_SSL_KEYFILE")
    def check_sv_ssl_keyfile(cls, keyfile: str) -> int:
        return validate.sv_ssl_keyfile(cls,keyfile)
    
    # SSL key file password
    SV_SSL_KEYFILE_PASS: str = ""

    #
    # DISCORD
    #

    # Discord API token
    DISCORD_TOKEN: str = ""
    
    # Discord server (guild) ID
    DISCORD_GUILD_ID: int = 0
    
    #
    # TEMPLATES
    #

    KAPI_URL: str = "http://127.0.0.1:3600"
    NODE_URL: str = "http://127.0.0.1:5052"
    OPERATOR_ID: int | None = None
    SIGN_PERCENT: int = 10
    VALIDATOR_EJECTOR_MESSAGE_FOLDER: str = ""
    ETHDO_VERSION: str = "1.35.2"
    ETHDO_URL: str = ""
    
    #
    # BUILD
    #

    DOCKERIZED: str = Field('', alias='__DOCKERIZED__') # env var "__DOCKERIZED__" without prefix
    STARTSCRIPT: str = Field('', alias='__STARTSCRIPT__') # env var "__STARTSCRIPT__" without prefix


settings = Settings()


# Define ETHDO_URL by ETHDO_VERSION
settings.ETHDO_VERSION = settings.ETHDO_VERSION.lower().replace("v","")
system_platform = platform.system()
if system_platform == "Darwin":
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{settings.ETHDO_VERSION}/ethdo-{settings.ETHDO_VERSION}-darwin-amd64.tar.gz"
elif system_platform == "Windows":
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{settings.ETHDO_VERSION}/ethdo-{settings.ETHDO_VERSION}-windows-exe.zip"
else:
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{settings.ETHDO_VERSION}/ethdo-{settings.ETHDO_VERSION}-linux-amd64.tar.gz"
settings.ETHDO_URL = ETHDO_URL