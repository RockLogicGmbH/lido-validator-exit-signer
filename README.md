# Exit Signer

A CLI and Docker solution to sign exit messages for the LIDO Validator Ejector.

# Options

Config options can be set as environment vars or defined in an .env file.

| Name                             | Default               | Required | Description                                                   |
| -------------------------------- | --------------------- | -------- | ------------------------------------------------------------- |
| KAPI_URL                         | http://127.0.0.1:3600 | Yes      | The URL to your KAPI service (usually http://127.0.0.1:3600)  |
| NODE_URL                         | http://127.0.0.1:5052 | Yes      | The URL to your Beacon Node (auto-detected for Stereum users) |
| OPERATOR_ID                      | ""                    | Yes      | Your LIDO Operator ID (auto-detected for Stereum users)       |
| VALIDATOR_EJECTOR_MESSAGE_FOLDER | ""                    | No       | Path to exit messages (auto-detected for Stereum users)       |
| ETHDO_VERSION                    | "1.35.2"              | No       | Version of ethdo executable to use for signing                |

# Dev

```
python main.py
```

> Requires Python 3.10 with Poetry and venv activated!

# Build

```
pyinstaller --onefile --name exitsigner main.py
```

# Prod

```
./exitsigner
```
