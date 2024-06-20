# Validator Exit Signer

A CLI <!-- and Docker--> solution to sign exit messages for the LIDO Validator Ejector.

# Options

Config options can be set as environment vars or defined in an .env file.

| Name                             | Default               | Required | Description                                                   |
| -------------------------------- | --------------------- | -------- | ------------------------------------------------------------- |
| KAPI_URL                         | http://127.0.0.1:3600 | Yes      | The URL to your KAPI service (usually http://127.0.0.1:3600)  |
| NODE_URL                         | http://127.0.0.1:5052 | Yes      | The URL to your Beacon Node (auto-detected for Stereum users) |
| OPERATOR_ID                      | ""                    | Yes      | Your LIDO Operator ID (auto-detected for Stereum users)       |
| SIGN_PERCENT                     | 10                    | No       | Percent of operators validators to sign exit messages for     |
| VALIDATOR_EJECTOR_MESSAGE_FOLDER | ""                    | No       | Path to exit messages (auto-detected for Stereum users)       |
| ETHDO_VERSION                    | "1.35.2"              | No       | Version of ethdo executable to use for signing                |

> SIGN_PERCENT can be overwritten using the `--sigpercent` argument

# Production

1. Login on your host where the LIDO Validator Ejector service is running
2. Switch to your root user or run all further commands with `sudo`
3. Create and change to a new/empty directory

```
mkdir ~/exit-signer
cd ~/exit-signer
```

4. Download the latest exitsigner executable for your Operating System from the [releases page on Github](https://github.com/RockLogicGmbH/lido-validator-exit-signer/releases), to your local system and name it `exitsigner` for example:

```
wget -O ./exitsigner https://github.com/RockLogicGmbH/lido-validator-exit-signer/releases/download/0.1.0/cli-ubuntu-latest
```

5. Give the exitsigner application execute permission

```
chmod +x ./exitsigner
```

6. Run the exitsigner application (optionally with --help)

```
./exitsigner [--help]
```

If you run the exitsigner on a host that is managed by [Stereum](https://github.com/stereum-dev/ethereum-node) you usually do not need to configure the application. Otherwise, or if you prefer, you can create a .env file via `./exitsigner --writeconfig` and adjust this as needed.

The process of signing exit messages for your validators can take from several minutes to several hours depending on the number to sing. You can expect an average of arround 30 seconds per validator.

Therefore it is highly recommended to run the exitsigner in an environment that you can leave while the process is ongoing. One of many solutions could be a screen session, for example:

Create a new screen session:

```
screen -S exitsig
```

Start the exitsigner process:

```
./exitsigner
```

- Then just paste the mnemonic to the already open input and press enter
- Press Ctrl+a (release) and then "d" to detach from the screen session (so it'll continue to run)

To re-attach to existing screen session run:

```
screen -S exitsig -dr
```

# Development

```
python main.py
```

> Requires Python 3.10 with Poetry and venv activated!

## Build

```
pyinstaller --onefile --name exitsigner main.py
```
