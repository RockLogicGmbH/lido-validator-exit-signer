import os
import sys
import argparse
import platform
import subprocess
from dotenv import load_dotenv
from functions import *

#
# CONFIG
#

# Load environment variables from .env file
load_dotenv()

# Default config values
default_values = {
    "KAPI_URL": "http://127.0.0.1:3600",
    "NODE_URL": "http://127.0.0.1:5052",
    "OPERATOR_ID": "",
    "SIGN_PERCENT": 10,
    "VALIDATOR_EJECTOR_MESSAGE_FOLDER": "",
    "ETHDO_VERSION": "1.37.3",
}

# Retrieve config values from environment or use defaults
NODE_URL = os.getenv("NODE_URL", default_values["NODE_URL"])
KAPI_URL = os.getenv("KAPI_URL", default_values["KAPI_URL"])
OPERATOR_ID = os.getenv("OPERATOR_ID", default_values["OPERATOR_ID"])
SIGN_PERCENT = int(os.getenv("SIGN_PERCENT", default_values["SIGN_PERCENT"]))
VALIDATOR_EJECTOR_MESSAGE_FOLDER = os.getenv("VALIDATOR_EJECTOR_MESSAGE_FOLDER", default_values["VALIDATOR_EJECTOR_MESSAGE_FOLDER"])
ETHDO_VERSION = os.getenv("ETHDO_VERSION", default_values["ETHDO_VERSION"])

# Define ETHDO_URL by ETHDO_VERSION
ETHDO_VERSION = ETHDO_VERSION.lower().replace("v","")
system_platform = platform.system()
if system_platform == "Darwin":
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{ETHDO_VERSION}/ethdo-{ETHDO_VERSION}-darwin-amd64.tar.gz"
elif system_platform == "Windows":
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{ETHDO_VERSION}/ethdo-{ETHDO_VERSION}-windows-exe.zip"
else:
    ETHDO_URL = f"https://github.com/wealdtech/ethdo/releases/download/v{ETHDO_VERSION}/ethdo-{ETHDO_VERSION}-linux-amd64.tar.gz"

# Show config values
# print(f"NODE_URL: {NODE_URL}")
# print(f"KAPI_URL: {KAPI_URL}")
# print(f"OPERATOR_ID: {OPERATOR_ID}")
# print(f"SIGN_PERCENT: {SIGN_PERCENT}")
# print(f"VALIDATOR_EJECTOR_MESSAGE_FOLDER: {VALIDATOR_EJECTOR_MESSAGE_FOLDER}")
# print(f"ETHDO_VERSION: {ETHDO_VERSION}")
# print(f"ETHDO_URL: {ETHDO_URL}")
# sys.exit()

#
# MAIN
#

# Main function
def main():

    # Set globals
    global VALIDATOR_EJECTOR_MESSAGE_FOLDER, NODE_URL, OPERATOR_ID, SIGN_PERCENT

    # Set script home directory
    SCRIPT_HOME_DIR = script_home_dir()

    # Move to script home directorxy
    os.chdir(SCRIPT_HOME_DIR)

    # Argument parsing setup
    parser = argparse.ArgumentParser(description='Exit Signer (Auto sign exit messages for LIDO validators by mnemonic)')
    parser.add_argument('--mnemonic', type=str, help='Specify the mnemonic directly (optional and strictly *not* recommended)')
    parser.add_argument('--signpercent', nargs='?', const=True, type=int, default=SIGN_PERCENT, help=f'Percent of validators managed by the operator to sign exit messages for (Default: {SIGN_PERCENT})')
    parser.add_argument('--writeconfig', action='store_true', help='Write .env file (if not exist) with default config values')
    parser.add_argument('--upgrade', action='store_true', help='Upgrade exitsigner application')
    parser.add_argument('--version', action='store_true', help='Get current version of the exitsigner')
    parser.add_argument('--debug', action='store_true', help='Expose debug infos')

    # Parse arguments
    args = parser.parse_args()

    # Handle --signpercent argument
    if args.signpercent:
        if not is_whole_number(args.signpercent) or args.signpercent > 100 or args.signpercent < 1:
            print("Invalid value for argument --signpercent (Expected range 1-100)")
            return
        SIGN_PERCENT=args.signpercent

    # Handle --writeconfig argument
    if args.writeconfig:
        if write_default_env_file(default_values):
            print("Default .env file created, adjust as needed.")
        else:
            print("Default .env file already exists")
        return
    
    # Handle --upgrade argument
    if args.upgrade:
        if not is_executable():
            print("Upgrades only run when packed as executable")
            return
        upgrade(SCRIPT_HOME_DIR)
        return
    
    # Handle --version argument
    if args.version:
        print(get_project_version())
        return

    # Check if user has elevated permission
    if not is_elevated_user():
        print("This application requires elevated permission!")
        return
    
    # Try to auto detect validatorejector directory
    VALIDATOR_EJECTOR_FOLDER = detect_validatorejector_directory()
    if args.debug:
        print(f"[DEBUG] VALIDATOR_EJECTOR_FOLDER = {VALIDATOR_EJECTOR_FOLDER}")

    # Auto detect validatorejector message directory if not defined in config
    if VALIDATOR_EJECTOR_MESSAGE_FOLDER == default_values["VALIDATOR_EJECTOR_MESSAGE_FOLDER"]:
        VALIDATOR_EJECTOR_MESSAGE_FOLDER = os.path.join(VALIDATOR_EJECTOR_FOLDER, "messages") if VALIDATOR_EJECTOR_FOLDER is not None else None
    if args.debug:
        print(f"[DEBUG] VALIDATOR_EJECTOR_MESSAGE_FOLDER = {VALIDATOR_EJECTOR_MESSAGE_FOLDER}")

    # Auto detect NODE_URL and OPERATOR_ID if not defined in config and VALIDATOR_EJECTOR_FOLDER could be found
    if VALIDATOR_EJECTOR_FOLDER:
        validator_ejector_config_id = os.path.basename(VALIDATOR_EJECTOR_FOLDER.replace("validatorejector-", ""))
        validator_ejector_yaml_file = f"/etc/stereum/services/{validator_ejector_config_id}.yaml"
        if args.debug:
            print(f"[DEBUG] validator_ejector_config_id = {validator_ejector_config_id}")
            print(f"[DEBUG] validator_ejector_yaml_file = {validator_ejector_yaml_file}")
        if os.path.exists(validator_ejector_yaml_file):
            validator_ejector_yaml_data = read_yaml_file(validator_ejector_yaml_file)
            NODE_URL = validator_ejector_yaml_data['env']['CONSENSUS_NODE'] if NODE_URL == default_values["NODE_URL"] else NODE_URL
            OPERATOR_ID = validator_ejector_yaml_data['env']['OPERATOR_ID'] if OPERATOR_ID == default_values["OPERATOR_ID"] else OPERATOR_ID
            if args.debug:
                print(f"[DEBUG] validator_ejector_yaml_data = ",validator_ejector_yaml_data)
                print(f"[DEBUG] NODE_URL = {NODE_URL}")
                print(f"[DEBUG] OPERATOR_ID = {OPERATOR_ID}")

    # Show config values
    # print(f"NODE_URL: {NODE_URL}")
    # print(f"KAPI_URL: {KAPI_URL}")
    # print(f"OPERATOR_ID: {OPERATOR_ID}")
    # print(f"SIGN_PERCENT: {SIGN_PERCENT}")
    # print(f"VALIDATOR_EJECTOR_MESSAGE_FOLDER: {VALIDATOR_EJECTOR_MESSAGE_FOLDER}")
    # print(f"ETHDO_VERSION: {ETHDO_VERSION}")
    # print(f"ETHDO_URL: {ETHDO_URL}")
    # sys.exit()

    # Check NODE_URL
    if not is_valid_url(NODE_URL):
        print("Setting NODE_URL invalid or not specified (Expected valid URL)")
        return
    
    # Check KAPI_URL
    if not is_valid_url(KAPI_URL):
        print("Setting KAPI_URL invalid or not specified (Expected valid URL)")
        return
    
    # Check OPERATOR_ID
    if not OPERATOR_ID or not is_whole_number(OPERATOR_ID):
        print("Setting OPERATOR_ID invalid or not specified")
        return
    
    # Check SIGN_PERCENT
    if not is_whole_number(SIGN_PERCENT) or SIGN_PERCENT > 100 or SIGN_PERCENT < 1:
        print("Setting SIGN_PERCENT invalid or not specified (Expected range 1-100)")
        return
    
    # Check VALIDATOR_EJECTOR_MESSAGE_FOLDER
    if not VALIDATOR_EJECTOR_MESSAGE_FOLDER:
        print("Could not find path to validatorejector messages folder (VALIDATOR_EJECTOR_MESSAGE_FOLDER)")
        return
    if "validatorejector" not in VALIDATOR_EJECTOR_MESSAGE_FOLDER:
        print("Path for setting VALIDATOR_EJECTOR_MESSAGE_FOLDER must contain 'validatorejector'")
        return
    if not VALIDATOR_EJECTOR_MESSAGE_FOLDER.endswith("messages"):
        print("Path for setting VALIDATOR_EJECTOR_MESSAGE_FOLDER must end with 'messages'")
        return
    if not os.path.exists(VALIDATOR_EJECTOR_MESSAGE_FOLDER):
        print("Path for setting VALIDATOR_EJECTOR_MESSAGE_FOLDER does not exist")
        return
    
    # Check ETHDO_VERSION
    if not is_semantic_version(ETHDO_VERSION):
        print("Setting ETHDO_VERSION invalid or not specified (Expected valid semantic version)")
        return
    
    # Check ETHDO_URL
    if not is_valid_url(ETHDO_URL):
        print("Setting ETHDO_URL invalid or not specified (Expected valid URL)")
        return

    # Install ethdo binary from GitHub
    print("Install ethdo")
    try:
        ethdo_path = install_ethdo(ETHDO_URL)
        if not ethdo_path:
            return 
    except Exception as e:
        print(f"Failed to install ethdo ({e})")
        return

    # Collect infos
    print("Collect validator data")
    
    # Get list of currently existing signed exit messages on Validator Ejector server
    existing_signed_exit_messages = []
    existing_signed_exit_messages_files = get_json_files(VALIDATOR_EJECTOR_MESSAGE_FOLDER)
    for filepath in existing_signed_exit_messages_files:
        filename_without_extension = os.path.splitext(os.path.basename(filepath))[0]
        existing_signed_exit_messages.append(filename_without_extension)

    # Get validators that need a signed exit message from KAPI
    jsonresult = get_validators_that_need_a_signed_exit_message_from_kapi(OPERATOR_ID, KAPI_URL,SIGN_PERCENT)
    if not jsonresult:
        return
    validators_that_need_a_signed_exit_message = jsonresult["data"]

    # Generate infos of messages that are active, burned or need to be generated
    existing_signed_exit_messages_active, existing_signed_exit_messages_burned, validators_that_have_no_signed_exit_message = [], [], []
    for validator in validators_that_need_a_signed_exit_message:
        if validator["key"] in existing_signed_exit_messages:
            existing_signed_exit_messages_active.append(validator["key"])
        else:
            validators_that_have_no_signed_exit_message.append(validator)
    for validatorkey in existing_signed_exit_messages:
        if validatorkey not in existing_signed_exit_messages_active:
            existing_signed_exit_messages_burned.append(validatorkey)

    print(f"Validators that need a signed exit message {len(validators_that_need_a_signed_exit_message)}")
    print(f"Existing signed exit messages on ejector server {len(existing_signed_exit_messages)}")
    print(f"Existing signed exit messages on ejector server that are active {len(existing_signed_exit_messages_active)}")
    print(f"Existing signed exit messages on ejector server that are burned {len(existing_signed_exit_messages_burned)}")
    print(f"Validators that have no signed exit message {len(validators_that_have_no_signed_exit_message)} (for each validator a signed exit messages need to be generated and added to ejector server)")

    if len(validators_that_have_no_signed_exit_message) < 1:
        print("SUCCESS: Currently no new exit messages needed to sign.")
        return
    
    # Handle MNEMONIC input
    if args.mnemonic:
        mnemonic = args.mnemonic
    else:
        while True:
            #mnemonic = input("Please enter mnemonic: ")
            mnemonic = get_secure_input("Please enter mnemonic: ")
            if validate_mnemonic(mnemonic):
                break
            else:
                print("Invalid mnemonic (expected at least 12 words splitted by space)")
    
    # Generate offline-preparation.json (this will generate all infos needed)
    print("Generate offline-preparation.json, please be patient..")
    offline_preparation_json = os.path.join(SCRIPT_HOME_DIR, 'offline-preparation.json')
    process = subprocess.run(f"{ethdo_path} --connection={NODE_URL} validator exit --json --verbose --debug --prepare-offline", capture_output=True, text=True, shell=True)
    exit_code = process.returncode
    err = process.stderr.strip()
    out = process.stdout.strip()
    if exit_code != 0:
        raise RuntimeError(f"Could not generate offline-preparation.json due to ethdo error ({err})")
    
    # For each validator generate a signed exit message with public key (must start with 0x)
    newmessages_total = 0
    newmessages_failed = 0
    #newmessages_tempdir = os.path.join(SCRIPT_HOME_DIR, 'newkeys')
    #create_directory(newmessages_tempdir)
    for validator in validators_that_have_no_signed_exit_message:
        validator_key = validator['key']
        #save_path = os.path.join(newmessages_tempdir, f"{validator_key}.json")
        save_path = os.path.join(VALIDATOR_EJECTOR_MESSAGE_FOLDER, f"{validator_key}.json")
        process = subprocess.run(f"{ethdo_path} --connection={NODE_URL} validator exit --json --verbose --debug --offline --max-distance=20480 --validator='{validator_key}' --mnemonic='{mnemonic}' > '{save_path}'", capture_output=True, text=True, shell=True)
        exit_code = process.returncode
        err = process.stderr.strip()
        out = process.stdout.strip()
        if exit_code != 0:
            newmessages_failed += 1
            last_line = get_last_line(err)
            print(f"Could not generate exit message for validator {validator_key} due to ethdo error ({last_line})")
            if os.path.exists(save_path):
                os.remove(save_path)            
            # if "mnemonic is invalid" in last_line:
            #     break
            # continue
            break
        newmessages_total += 1
        print(f"Generated exit message for validator {validator_key} ({validator['validatorIndex']})")
    
    # Remove offline_preparation_json if exists
    if os.path.exists(offline_preparation_json):
        os.remove(offline_preparation_json)
        
    # Success or fail
    if newmessages_failed > 0:
        print(f"ERROR: Failed to create {newmessages_failed} new signed exit messages ({newmessages_total} new signed exit messages created successfully).") 
    else:
        print(f"SUCCESS: {newmessages_total} new signed exit messages successfully created.")
#
# LOAD
#

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("")
        print("Aborted.")
        pass
    except Exception as e:
        print(e)
