import ctypes
import getpass
import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
import zipfile
import paramiko
import requests
import oyaml as yaml
import hashlib
import validators
import semver
from pathlib import Path
import toml
import semver
from semver import Version
from typing import Optional, Tuple

# SemVer class to compare semantic versions
# Requires Python semver package
# Examples:
# say(SemVer.compare("1.3.2", "1.3.3")) # -1
# say(SemVer.compare("1.3.3", "1.3.3")) # 0
# say(SemVer.compare("1.3.3", "1.3.2")) # 1
class SemVer:
    # Cleanup string for semantic versions
    @staticmethod
    def get_version_tuple(version: str) -> Tuple[Version, Optional[str]]:
        """
        Convert an incomplete version string into a semver-compatible Version
        object

        * Tries to detect a "basic" version string (``major.minor.patch``).
        * If not enough components can be found, missing components are
            set to zero to obtain a valid semver version.

        :param str version: the version string to convert
        :return: a tuple with a :class:`Version` instance (or ``None``
            if it's not a version) and the rest of the string which doesn't
            belong to a basic version.
        :rtype: tuple(:class:`Version` | None, str)
        """
        BASEVERSION = re.compile(
            r"""[vV]?
                (?P<major>0|[1-9]\d*)
                (\.
                (?P<minor>0|[1-9]\d*)
                (\.
                    (?P<patch>0|[1-9]\d*)
                )?
                )?
            """,
            re.VERBOSE,
        )
        match = BASEVERSION.search(version)
        if not match:
            return (None, version)

        ver = {
            key: 0 if value is None else value for key, value in match.groupdict().items()
        }
        ver = Version(**ver)
        rest = match.string[match.end() :]  # noqa:E203
        return ver, rest

    # Helper for semantic versions
    @staticmethod
    def version_tuple_to_string(version_tuple):
        version_str = f"{version_tuple[0].major}.{version_tuple[0].minor}.{version_tuple[0].patch}" \
                    f"{'-' + version_tuple[0].prerelease if version_tuple[0].prerelease else ''}" \
                    f"{'.' + version_tuple[0].build if version_tuple[0].build else ''}" \
                    f"{version_tuple[1]}"
        return version_str

    # Compare version (in a none fully strict fashion)
    @staticmethod
    def compare(version1, version2):
        version1_tuple = SemVer.get_version_tuple(version1)
        version2_tuple = SemVer.get_version_tuple(version2)
        version1 = SemVer.version_tuple_to_string(version1_tuple)
        version2 = SemVer.version_tuple_to_string(version2_tuple)
        return semver.compare(version1, version2)

#
# FUNCTIONS
#

# Flush all output function
def say(txt):
    print(txt,flush=True)

# Custom filter to compare semantic versions
# Returns True if current_version is lower than most_recent_version
# Examples:
# say(is_lower_than("1.3.2", "1.3.3")) # True (Internal: -1)
# say(is_lower_than("1.3.3", "1.3.3")) # False (Internal: 0)
# say(is_lower_than("1.3.3", "1.3.2")) # False (Internal: 1)
def is_lower_than(current_version, most_recent_version):
    return SemVer.compare(current_version, most_recent_version) < 0

# Check if string is a semantic version at all
def is_semantic_version(version):
    try:
        semver.parse_version_info(version)
        return True
    except ValueError:
        return False
    
# Chekc for valid URL
def is_valid_url(url):
    return validators.url(url)

# Generate .env file (if not exist) with default config settings
def write_default_env_file(default_values):
    """Write or update .env file with default configuration values."""
    env_file_path = os.path.join(script_home_dir(), '.env')
    if not os.path.exists(env_file_path):
        with open(env_file_path, 'w') as f:
            for key, value in default_values.items():
                f.write(f"# {key}={value}\n")
        return env_file_path
    return False

def sha256_hash_file(filename):
    # Initialize the hash object
    sha256_hash = hashlib.sha256()

    try:
        # Open the file in binary mode
        with open(filename, "rb") as f:
            # Read and update hash in chunks of 4K
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        # Get the hexadecimal representation of the hash
        hex_digest = sha256_hash.hexdigest()
        return hex_digest

    except FileNotFoundError:
        say(f"File '{filename}' not found.")
        return None
    except IOError as e:
        say(f"Error reading '{filename}': {e}")
        return None
    
# Function to download ethdo from Github
def install_ethdo(url, exitsigner_tmp_dir=None, dockerized=False):
    filename = os.path.basename(urlparse(url).path)
    extension = os.path.splitext(filename)[1].lower()
    temp_dir = tempfile.gettempdir()
    if exitsigner_tmp_dir and temp_dir not in exitsigner_tmp_dir:
        raise ValueError("Exitsigner temp directory must be inside system temp directory!")
    tar_file_path = os.path.join(temp_dir, filename)
    extracted_dir = os.path.join(temp_dir, "ethdo-extracted")
    ethdo_temp_dir = exitsigner_tmp_dir if exitsigner_tmp_dir else os.path.join(temp_dir, 'ethdo-bin')
    final_ethdo_path = os.path.join(ethdo_temp_dir, 'ethdo') if not dockerized else "/usr/local/bin/ethdo"

    # Check if ethdo is already installed
    if os.path.exists(final_ethdo_path):

        # Check version
        process = subprocess.run(f"{final_ethdo_path} version", capture_output=True, text=True, shell=True)
        exit_code = process.returncode
        err = process.stderr.strip()
        out = process.stdout.strip()
        if exit_code != 0:
            raise RuntimeError(f"Could not determine ethdo version ({err})")
        ethdo_version = out
        match = re.search(r'/v(\d+\.\d+\.\d+)/', url)
        if match:
            ethdo_installer_version = match.group(1)
        else:
            raise RuntimeError(f"Could not determine ethdo version from latest installer url ({err})")
        
        # If the version is equal its already installed, otherwise new version must be installed
        if ethdo_installer_version == ethdo_version:
            say(f"Executable v{ethdo_version} of ethdo already installed")
            return final_ethdo_path

    # Download the tarball
    response = requests.get(url)
    with open(tar_file_path, "wb") as f:
        f.write(response.content)

    # Verify the tarball hash
    response = requests.get(f"{url}.sha256")
    hash = response.content.strip().decode('utf-8')
    if sha256_hash_file(tar_file_path) != hash:
        os.remove(tar_file_path)
        say("Failed to install ethdo (Invalid tarball hash)")
        return None

    # Extract the file based on the extension
    if extension == ".tar.gz" or extension == ".tgz" or extension == ".gz":
        with tarfile.open(tar_file_path, "r:gz") as tar:
            tar.extractall(extracted_dir)
    elif extension == ".zip":
        with zipfile.ZipFile(tar_file_path, "r") as zip_ref:
            zip_ref.extractall(extracted_dir)
    else:
        os.remove(tar_file_path)
        say("Failed to install ethdo (Unsupported file format)",extension)
        return None

    # Move the extracted binary to /usr/local/bin
    extracted_file_path = os.path.join(extracted_dir, "ethdo")
    os.rename(extracted_file_path, final_ethdo_path)

    # Clean up - remove the tarball and extracted directory
    os.remove(tar_file_path)
    os.rmdir(extracted_dir)
    say("Successfully installed ethdo executable")
    return final_ethdo_path

# Auto detect validatorejector home directory
def detect_validatorejector_directory(expected_home_directory="/opt/stereum"):
    # Directory to search in
    directory_path = expected_home_directory

    # Define the pattern to search for
    pattern = 'validatorejector-*'

    # Construct the full path pattern
    full_pattern = os.path.join(directory_path, pattern)

    # Use glob to find directories matching the pattern
    matching_folders = glob.glob(full_pattern)

    # Warn on multiple matches
    if len(matching_folders) > 1:
        say(f"Warning: Found multiple validatorejector directories in {directory_path}. Using the first match.")
        for folder in matching_folders:
            say(f"Found folder: {folder}")

    # Return the first match (or None if no match)
    return matching_folders[0] if matching_folders else None

# Check if given num is numeric and a whole number
# Note that also string "3" is considered a whole number alson as strict is False (default)
# Test cases:
# say(is_whole_number(3))           # True
# say(is_whole_number(1.5))         # False
# say(is_whole_number("3"))         # True (strict=False)
# say(is_whole_number("1.5"))       # False (strict=False)
# say(is_whole_number("3.0"))       # True (strict=False)
# say(is_whole_number("abc"))       # False
# say(is_whole_number(True))        # False
# say(is_whole_number(None))        # False
# say("--- Strict mode ---")
# say(is_whole_number("3", strict=True))       # False (strict=True)
# say(is_whole_number("1.5", strict=True))     # False (strict=True)
# say(is_whole_number("3.0", strict=True))     # False (strict=True)
# say(is_whole_number(True, strict=True))      # False (strict=True)
def is_whole_number(num, strict=False):
    if isinstance(num, bool):
        # For boolean values, return False as they are not considered whole numbers
        return False
    elif isinstance(num, (int, float)):
        # Check if num is numeric (either int or float)
        if isinstance(num, int):
            # If num is an integer, return True directly
            return True
        else:
            # If num is a float, check if it is a whole number
            return num.is_integer()
    elif isinstance(num, str):
        if strict:
            # If strict is True, we do not allow strings that represent numbers
            return False
        else:
            # Check if num is a string representing a numeric value
            try:
                float_num = float(num)
                return float_num.is_integer()
            except ValueError:
                return False
    else:
        # num is not numeric or a string
        return False
    
# Function to get validators that need signed exit messages from KAPI
def get_validators_that_need_a_signed_exit_message_from_kapi(operator_id, kapi_url, percent=10):
    if not is_whole_number(operator_id):
        if operator_id:
            say(f'Invalid operator id "{operator_id}" for KAPI request specified')
        else:
            say(f'No operator id for KAPI request specified') 
        return False
    try:
        percent = percent if is_whole_number(percent) and percent > 0 and percent <= 100 else 10
        result = requests.get(f"{kapi_url}/v1/modules/1/validators/validator-exits-to-prepare/{operator_id}?percent={percent}")
        if result.status_code == 200:
            jsonresp = result.json()
            if "data" in jsonresp:
                return jsonresp
            say(f"KAPI responded with invalid format (data key missing)")
            return False
        else:
            say(f"Request to KAPI failed with status code: {result.status_code}")
            return False
    except Exception as e:
            say(f"Request to KAPI failed with error: {e}")
            return False

# Get first key from list where value contains "search"
# Example
# my_list = ["myaaaxxx", "mybbbxxx", "mycccxxx"]
# say(get_key(my_list, "bbb"))  # Output: 1
# say(get_key(my_list, "bbb", exact=True))  # Output: None
def get_key(lst, search, exact=False):
    for idx, item in enumerate(lst):
        if exact:
            if item == search:
                return idx
        else:
            if search in item:
                return idx
    return None

# Get all json files in given path as list
def get_json_files(path):
    """
    Get a list of JSON file names matching the pattern '0x*.json' in the specified directory path.

    Args:
    - path (str): Directory path where the JSON files are located.

    Returns:
    - list: List of JSON file names.
    """
    # Construct the pattern to match files (0x*.json)
    file_pattern = os.path.join(path, '0x*.json')

    # Use glob to find all files matching the pattern
    matching_files = glob.glob(file_pattern)

    # Return the list of matching files
    return matching_files

# Create directory with sub directories
def create_directory(directory_path):
    try:
        # Create target directory & all intermediate directories if they don't exist
        os.makedirs(directory_path)
        #say(f"Directory '{directory_path}' created successfully.")
    except FileExistsError:
        pass
        #say(f"Directory '{directory_path}' already exists.")
    except OSError as e:
        say(f"Error creating directory '{directory_path}': {e}")

# Returns script home directory
def script_home_dir():
    if getattr(sys, 'frozen', False):
        # Running in a bundled executable (e.g., created by PyInstaller)
        script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        # Running as a script
        script_dir = os.path.dirname(os.path.realpath(__file__))
    return script_dir

# Returns true if running in a bundled executable (e.g., created by PyInstaller)
def is_executable():
    if getattr(sys, 'frozen', False):
        return True
    return False

# Return true if user is elevated (sudo/root/admin) in win/lin/mac
def is_elevated_user():
    system = platform.system()
    
    if system == "Linux" or system == "Darwin":  # Linux or macOS
        return os.geteuid() == 0  # Check if effective user ID is 0 (root)
    
    elif system == "Windows":  # Windows
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    
    else:
        say(f"Unsupported operating system: {system}")
        return False
    
# Get last line from string
def get_last_line(text):
    # Split the text into lines using newline as the delimiter
    lines = text.splitlines()

    # Check if there are lines in the text
    if lines:
        # Return the last line
        return lines[-1]
    else:
        # Return None or handle the case where there are no lines
        return None
    
# Get input without visibility on CLI
def get_secure_input(prompt):
    try:
        # Use getpass to get secure input (like password input)
        secure_input = getpass.getpass(prompt)
        return secure_input.strip()  # Strip any extra whitespace
    except Exception as e:
        say(f"Error getting secure input: {e}")
        return None
    
# Validate MNEMONIC format
def validate_mnemonic(mnemonic):
    # Check if the input contains at least 12 words split by spaces or tabs
    words = mnemonic.split()
    if len(words) >= 12:
        return True
    else:
        return False
    
# Read yaml file and return object
def read_yaml_file(file_path):
    with open(file_path, 'r') as file:
        try:
            yaml_data = yaml.safe_load(file)
            return yaml_data
        except yaml.YAMLError as e:
            say(f"Error reading YAML file: {e}")
            return None
        

# Get infos of "latest" release from "owner/repo" via GitHub API
# # Examples: 
# github_owner = "RockLogicGmbH"
# github_repo = "lido-validator-exit-signer"
# github_keys = ["tag_name", "name", "draft", "prerelease", "body"]
# result = get_latest_release_info(github_owner,github_repo)
# say(result)
# say(result["tag_name"])
# result = get_latest_release_info(github_owner,github_repo,github_keys)
# say(result)
# say(result["tag_name"])
# sys.exit(3)
def get_latest_release_info(owner, repo, keys = [], timeout=5, token="", silent=False, raiseEx=False):
    if repo == "notifications":
        if not silent:
            say(f"Avoid to fetch latest release info for {owner}/{repo}")
        return None
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        response = requests.get(url,timeout=timeout,headers=headers)
        if response.status_code == 200:
            release_info = response.json()
            return {key: release_info.get(key) for key in keys} if len(keys) > 0 else release_info
        else:
            err = f"Failed to fetch latest release info for {owner}/{repo}. Status code: {response.status_code}"
            if raiseEx:
                raise Exception(err)
            if not silent:
                say(err)
            return None
    except Exception as e:
        err = f"Failed to fetch latest release info for {owner}/{repo} ({e})"
        if raiseEx:
            raise Exception(err)
        if not silent:
            say(err)
        return None
    

# Get project version from toml
# https://stackoverflow.com/a/78082532    
def get_project_version():
    version = "0.0.0"
    # adopt path to your pyproject.toml
    pyproject_toml_file = Path(__file__).parent / "pyproject.toml"
    if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
        data = toml.load(pyproject_toml_file)
        # check project.version
        if "project" in data and "version" in data["project"]:
            version = data["project"]["version"]
        # check tool.poetry.version
        elif "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]:
            version = data["tool"]["poetry"]["version"]
    return version

# Get latest release infos for exitsigner based on OS
def get_latest_release_infos_for_os(github_owner = "RockLogicGmbH", github_repo = "lido-validator-exit-signer"):
    release = get_latest_release_info(github_owner,github_repo)
    system_platform = platform.system()
    if system_platform == "Darwin":
        find = "macos"
    elif system_platform == "Windows":
        find = "windows"
    else:
        find = "ubuntu"
    if release["assets_url"]:
        response = requests.get(release["assets_url"])
        assets = response.json()
        #say(data)
        osasset = None
        for asset in assets:
            #say(asset["name"])
            #say(f"exitsigner-{find}-latest")
            if asset["name"] == f"exitsigner-{find}-latest" or asset["name"] == f"cli-{find}-latest":
                osasset = asset
                break;
    return {
        "version": release["tag_name"], # Version a.k.a "tag_name" of the latest release
        "release": release, # All infos of the latest release
        "assets": assets,   # assets for this release
        "asset": osasset,   # asset associated to the OS the application is currently runnign on (None if undetected)
        "download": osasset["browser_download_url"] if osasset else None,   # Asset download URL (None if undetected)
    }

# Upgrade existsigner
def upgrade(SCRIPT_HOME_DIR):
    local_file_path = os.path.join(SCRIPT_HOME_DIR,"exitsigner")
    if not os.path.exists(local_file_path):
        say("Invalid SCRIPT_HOME_DIR specified")
        return False
    try:
        latest_release_for_os = get_latest_release_infos_for_os()
        current_version = get_project_version()
        # say(latest_release_for_os["version"])
        # say(latest_release_for_os["download"])
        # say(current_version)
        if is_lower_than(current_version, latest_release_for_os["version"]):
            say("Uprading exitsigner...")
            # Download and overwrite the binary
            url = latest_release_for_os["download"];
            response = requests.get(url)
            with open(local_file_path, "wb") as f:
                f.write(response.content)
                say(f"Successfully upgraded exitsigner to version {latest_release_for_os['version']}")
                return True
        else:
            say(f"The exitsigner application is already at the newest version {current_version}")
            return True
    except Exception as e:
        say("Could not get latest exitsigner release infos ({e})")
    return False

# Move signed message
def move_signed_message(save_path_temp,save_path_live,chmod=600,chown="root:root"): 
    # First, by default adjust owner and permissions to 600/root:root on the temp file
    if chmod and platform.system() == "Linux":
        os.chmod(save_path_temp, int(oct(chmod), 8))
    if chown and platform.system() == "Linux":
        if not ":" in chown:
            raise ValueError("Argument 'chown' must be in format 'user:group'")
        r = chown.split(":")
        user = r[0]
        group = r[1]
        shutil.chown(save_path_temp, user=user, group=group)
        
    # Finally, move the temp file to validator ejector directory
    shutil.move(save_path_temp,save_path_live)

    # Success
    return True

# Format drykey
def format_drykey(drykey:str):
    drykey = drykey.rstrip()
    if drykey.endswith(".json"):
        drykey = drykey[:-5]
    if not drykey.startswith("0x"):
        raise ValueError("Invalid drykey specified (Does not start with 0x)") 
    if len(drykey) != 98:
        raise ValueError("Invalid drykey specified (Length not 98 characters)")
    validators_that_have_no_signed_exit_message = [{
        'validatorIndex': 0, # not used anyway but keep format for the test key
        'key': drykey
    }]
    return drykey, validators_that_have_no_signed_exit_message

#
# BEACON HELPER
#

# Get network name frok beacon node
def get_network_from_beacon_node(beacon_node_url):
    networks = {
        "1" : "mainnet",
        "17000" : "holesky",
        "11155111" : "sepolia",
    }
    try:
        chain_id = get_chain_id_from_beacon_node(beacon_node_url)
        return networks.get(chain_id,"unknown")
    except:
        return "unknown"

# Get curretn chain id from Beacon API ("/eth/v1/config/deposit_contract")
# Mainnet = 1 | Holesky = 17000 | Sepolia = 11155111 | ....
# https://besu.hyperledger.org/24.5.2/public-networks/concepts/network-and-chain-id
# https://chainid.network/
# https://github.com/ethereum-lists/chains
def get_chain_id_from_beacon_node(beacon_node_url):
    url = f"{beacon_node_url}/eth/v1/config/deposit_contract"
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json().get('message'))
    chain_id = response.json().get("data", {}).get("chain_id")
    if not chain_id:
        raise ValueError("Key chain_id not set or empty")
    return chain_id

# Check via Beacon API if validator exists on chain of the given node url
# Note, status "active_ongoing" is what should be expected from an active validator
def check_validator_by_beacon_node(beacon_node_url,valudator_key,expect_status=None):
    url = f"{beacon_node_url}/eth/v1/beacon/states/head/validators/{valudator_key}"
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json().get('message'))
    status = response.json().get("data", {}).get("status")
    if not status:
        raise ValueError("Key 'status' not set or empty")
    if expect_status and status != expect_status:
        raise ValueError(f"Unexpected validator status '{status}' [Expected: {expect_status}]")
    return status

#
# REMOTE STUFF
#

# Function to establish SSH connection
def establish_ssh_connection(address, username, key_filename=None, password=None, timeout=2):
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(address, username=username, key_filename=key_filename, password=password, timeout=timeout)
    return ssh_client;

def get_exit_messages_to_sign_from_kapi(operator_id, kapi_url):
    result = requests.get(f"{kapi_url}/v1/modules/1/validators/validator-exits-to-prepare/{operator_id}")
    if result.status_code == 200:
        jsonresp = result.json()
        if "data" in jsonresp:
            return jsonresp
        say(f"KAPI reponded invalid format (data key missing)")
        return False
    else:
        say(f"Request failed with status code: {result.status_code}")
        return False
    
# Run ssh command(s) as root
# Examples:
# ssh_exec_elevated(ssh_client, "whoami")
# ssh_exec_elevated(ssh_client, ["cd /root", "ls -la"])
def ssh_exec_elevated(ssh_client, commands=[]):
    if isinstance(commands, str):
        commands = [commands]
    if commands:
        command = 'sudo -i bash -c "' + " && ".join(commands) + '"'
        stdin, stdout, stderr = ssh_client.exec_command(command)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        exitcode = stdout.channel.recv_exit_status()
    else:
        exitcode = "3"
        out = ""
        err = "No command specified"
    return {
        "exitcode": exitcode,
        "stdout": out,
        "stderr": err,
    }

def toLinPath(p):
    return p.replace(os.sep,"/") if isinstance(p,str) else p

# Auto detect validatorejector home directory via SSH
def detect_validatorejector_directory_by_ssh(ssh_client,expected_home_directory="/opt/stereum"):

    # Directory to search in
    directory_path = expected_home_directory

    # Define the pattern to search for
    pattern = 'validatorejector-*'
    #pattern = '*-*'

    # Replace directory_path and pattern with forward slahes
    # since the connection goes to a Linux host in ANY case!
    directory_path = toLinPath(directory_path)
    pattern = toLinPath(pattern)

    #say(f"directory_path = {directory_path}")
    #say(f"pattern = {pattern}")

    # Find directories matching the pattern on Validator Ejector server
    result = ssh_exec_elevated(ssh_client, f"find '{directory_path}' -maxdepth 1 -type d -name '{pattern}'")
    if result["exitcode"]:
        say(f"Coud not auto detect validatorejector directory ({result['stderr']})")
        return None
    #say(result["stdout"])
    matching_folders = result["stdout"].strip().splitlines()

    # Warn on multiple matches
    if len(matching_folders) > 1:
        say(f"Warning: Found multiple validatorejector directories in {directory_path}. Using the first match.")
        for folder in matching_folders:
            say(f"Found folder: {folder}")

    # Return the first match (or None if no match)
    return matching_folders[0] if matching_folders else None

# Read yaml file and return object
def read_yaml_file_by_ssh(ssh_client,file_path):
    # Read the YAML file content remotely
    result = ssh_exec_elevated(ssh_client, f"cat '{file_path}'")
    if result["exitcode"]:
        say(f"Error reading remote yaml file {file_path} ({result['stderr']})")
        return None
    
    # Parse the YAML content
    try:
        yaml_data = yaml.safe_load(result["stdout"])
        return yaml_data
    except yaml.YAMLError as e:
        say(f"Error parsing YAML content from {file_path}: {e}")
        return None

# Get all json files on remote server in given path as list
def get_json_files_by_ssh(ssh_client,path):
    """
    Get a list of JSON file names from remote server matching the pattern '0x*.json' in the specified directory path.

    Args:
    - ssh_client (obj): SSH client object
    - path (str): Directory path on the remote server where the JSON files are located.

    Returns:
    - list: List of JSON file names.
    """
    # Directory to search in
    directory_path = path

    # Construct the pattern to match files (0x*.json)
    pattern = '0x*.json'
    #pattern = '*-sdsdggd*'

    # Replace directory_path and pattern with forward slahes
    # since the connection goes to a Linux host in ANY case!
    directory_path = toLinPath(directory_path)
    pattern = toLinPath(pattern)

    #say(f"directory_path = {directory_path}")
    #say(f"pattern = {pattern}")

    # Return the list of matching files
    matching_files = []

    # Find files matching the pattern on Validator Ejector server
    result = ssh_exec_elevated(ssh_client, f"find '{directory_path}' -maxdepth 1 -type f -name '{pattern}'")
    if result["exitcode"]:
        say(f"Coud not find JSON files on remote server ({result['stderr']})")
        # stay compatible with get_json_files and return an empty list insteadf of None
        return matching_files
    matching_files += result["stdout"].strip().splitlines()

    # Return the list of matching files
    return matching_files

# Uplaods file via SCP/SFTP
def upload_file_via_scp(ssh_client, local_file_path, remote_file_path, raiseExceptions = False):
    try:
        sftp = ssh_client.open_sftp()
        sftp.put(local_file_path, remote_file_path)
        sftp.close()
        return True
    except Exception as e:
        if raiseExceptions:
            raise e
        say(f"Error uploading file: {e}")
        return None

# Upload signed message
def upload_signed_message(ssh_client,save_path_local,save_path_remote,chmod=600,chown="root:root"): 
    # First upload to tmp directory with prefix
    temp_path_remote = f"/tmp/_signedmsg_" + os.path.basename(save_path_local)
    upload_file_via_scp(ssh_client, save_path_local, temp_path_remote, raiseExceptions=True)
 
    # Second, by default adjust owner and permissions to 600/root:root on the temp file
    if chmod:
        result = ssh_exec_elevated(ssh_client, f"chmod {chmod} '{temp_path_remote}'")
        if result["exitcode"]:
            raise RuntimeError(result['stderr'])
    if chown:
        result = ssh_exec_elevated(ssh_client, f"chown {chown} '{temp_path_remote}'")
        if result["exitcode"]:
            raise RuntimeError(result['stderr'])
        
    # Third, move the temp file as root to validator ejector directory
    result = ssh_exec_elevated(ssh_client, f"mv '{temp_path_remote}' '{save_path_remote}'")
    if result["exitcode"]:
        raise RuntimeError(result['stderr'])

    # Success
    return True