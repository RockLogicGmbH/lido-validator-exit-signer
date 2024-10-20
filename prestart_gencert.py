import asyncio
import subprocess
import sys
import os
from loguru import logger
from config.logger import LOG_LEVEL, setup_logging
from os.path import isfile, isdir
import shutil

setup_logging(LOG_LEVEL, False)


# if ! [ -f "certs/selfsigned.crt" ] || ! [ -f "certs/selfsigned.key" ] || ! openssl x509 -checkend 0 -noout -in "certs/selfsigned.crt" &>/dev/null; then
#     openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj "/C=AT/ST=MyState/L=MyCity/O=MyOrg/OU=MyOrgUnit/CN=MyHostName" -keyout certs/selfsigned.key -out certs/selfsigned.crt &>/dev/null
# fi

# This checks and/or generates SSL certifictes via shell for better logging
async def run_gencert() -> None:
        # Get expiration: "openssl x509 -checkend 0 -noout -in "certs/selfsigned.crt""
        check_expiration = False # Set this True manually and recompile the container to check cert expiration!
        expired = False
        if check_expiration and isfile("certs/selfsigned.crt"):
            process = subprocess.Popen(
                ['openssl', 'x509', '-checkend', '0', '-noout', '-in', 'certs/selfsigned.crt'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.wait(timeout = 15)
            if process.returncode > 0:
                logger.info("Existing self-signed SSL certificates expired")
                expired = True

        if isfile("certs/selfsigned.crt") and isfile("certs/selfsigned.key") and not expired:
            logger.info("Existing self-signed SSL certificates ok")
            return True
        
        if not isdir("certs"):
            os.makedirs("certs")
        
        if isdir("certs/selfsigned.crt"): # trash dir created by docker compose
            raise FileExistsError("certs/selfsigned.crt is a directory!")
        
        if isdir("certs/selfsigned.key"): # trash dir created by docker compose
            raise FileExistsError("certs/selfsigned.key is a directory!")

        # Create cert: "openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj "/C=AT/ST=MyState/L=MyCity/O=MyOrg/OU=MyOrgUnit/CN=MyHostName" -keyout certs/selfsigned.key -out certs/selfsigned.crt"  (throw exception on error)
        process = subprocess.Popen(
            [
                'openssl',
                'req',
                '-x509',
                '-nodes',
                '-days',
                '365',
                '-newkey',
                'rsa:2048',
                '-subj',
                '/C=AT/ST=MyState/L=MyCity/O=MyOrg/OU=MyOrgUnit/CN=MyHostName',
                '-keyout',
                'certs/selfsigned.key',
                '-out',
                'certs/selfsigned.crt'
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        while True:
            output = process.stdout.readline().strip()
            if output:
                logger.info(output)
            return_code = process.poll()
            if return_code is not None:
                if return_code > 0:
                    for output in process.stderr.readlines():
                        output = output.strip()
                    raise Exception(output)
                break
        logger.info("Created new self-signed SSL certificates")

async def main() -> None:
    logger.info("Check self-signed SSL certificates")
    try:
        await run_gencert()
        logger.success("Successfully checked self-signed SSL certificates")
    except Exception as e:
        logger.error(f"Could not check self-signed SSL certificates ({str(e)})")
        sys.exit(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error(f"Service startup aborted")
        sys.exit(4)