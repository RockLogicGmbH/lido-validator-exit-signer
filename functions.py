import ctypes
import getpass
import glob
import os
import platform
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlparse
import zipfile
import requests
import oyaml as yaml
import hashlib

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
        print(f"File '{filename}' not found.")
        return None
    except IOError as e:
        print(f"Error reading '{filename}': {e}")
        return None
    
# Function to download ethdo from Github
def install_ethdo(url,dockerized=False):
    filename = os.path.basename(urlparse(url).path)
    extension = os.path.splitext(filename)[1].lower()
    tar_file_path = f"./{filename}"
    extracted_dir = f"./tmp"
    final_ethdo_path =  "./ethdo" if not dockerized else "/usr/local/bin/ethdo"

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
            print(f"Executable v{ethdo_version} of ethdo already installed")
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
        print("Failed to install ethdo (Invalid tarball hash)")
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
        print("Failed to install ethdo (Unsupported file format)",extension)
        return None

    # Move the extracted binary to /usr/local/bin
    extracted_file_path = os.path.join(extracted_dir, "ethdo")
    os.rename(extracted_file_path, final_ethdo_path)

    # Clean up - remove the tarball and extracted directory
    os.remove(tar_file_path)
    os.rmdir(extracted_dir)
    print("Successfully installed ethdo executable")
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
        print(f"Warning: Found multiple validatorejector directories in {directory_path}. Using the first match.")
        for folder in matching_folders:
            print(f"Found folder: {folder}")

    # Return the first match (or None if no match)
    return matching_folders[0] if matching_folders else None

# Function to get validators that need signed exit messages from KAPI
def get_validators_that_need_a_signed_exit_message_from_kapi(operator_id, kapi_url):
    result = requests.get(f"{kapi_url}/v1/modules/1/validators/validator-exits-to-prepare/{operator_id}")
    if result.status_code == 200:
        jsonresp = result.json()
        if "data" in jsonresp:
            return jsonresp
        print(f"KAPI responded with invalid format (data key missing)")
        return False
    else:
        print(f"Request failed with status code: {result.status_code}")
        return False

# Get first key from list where value contains "search"
# Example
# my_list = ["myaaaxxx", "mybbbxxx", "mycccxxx"]
# print(get_key(my_list, "bbb"))  # Output: 1
# print(get_key(my_list, "bbb", exact=True))  # Output: None
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
        #print(f"Directory '{directory_path}' created successfully.")
    except FileExistsError:
        pass
        #print(f"Directory '{directory_path}' already exists.")
    except OSError as e:
        print(f"Error creating directory '{directory_path}': {e}")

# Returns script home directory
def script_home_dir():
    if getattr(sys, 'frozen', False):
        # Running in a bundled executable (e.g., created by PyInstaller)
        script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        # Running as a script
        script_dir = os.path.dirname(os.path.realpath(__file__))
    return script_dir

# Return true if user is elevated (sudo/root/admin) in win/lin/mac
def is_elevated_user():
    system = platform.system()
    
    if system == "Linux" or system == "Darwin":  # Linux or macOS
        return os.geteuid() == 0  # Check if effective user ID is 0 (root)
    
    elif system == "Windows":  # Windows
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    
    else:
        print(f"Unsupported operating system: {system}")
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
        print(f"Error getting secure input: {e}")
        return None
    
# Validate MNEMONIC format
def validate_mnemonic(mnemonic):
    # Check if the input contains exactly 24 words split by spaces or tabs
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
            print(f"Error reading YAML file: {e}")
            return None
