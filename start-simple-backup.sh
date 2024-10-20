#!/bin/bash
# -----------------------------------------------------------------------------
# What: Simple backup (Stop App, do file and database backup, start App)
# Usage: bash start-backup.sh
# Note: Backups are stored in ../backups/YYYYMMDDHHIISS-<appname>
# -----------------------------------------------------------------------------

#
# HEADER
#

# Make sure piped errors will result in $? (https://unix.stackexchange.com/a/73180/452265)
set -o pipefail
	
# Set path manually since the script is maybe called via cron!
PATH=~/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

#
# CONFIG
#

# init main vars
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SCRIPTDIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
SCRIPTNAME=$(basename "$SOURCE")
SCRIPTPATH="$SCRIPTDIR/$SCRIPTNAME"
SCRIPTUSER=$(whoami)
SCRIPTALIAS="${SCRIPTNAME%.*}"
USER=$(whoami)
HOST=$(hostname -s)
CURRENTDIR="$PWD"
HOST_NAME="$(hostname)"                                             # e.g. -> server1
OS_NAME="$(cat /etc/issue 2>/dev/null | awk -F " " '{print $1}')"   # e.g. -> Ubuntu
GLOBALBACKUPSDIR="$SCRIPTDIR/../backups"

#
# FUNCTIONS
#

# output default message
say() {
    echo "$@"
}

# exit script with error message and error code
die() {
    echo "$@" >&2
    exit 3
}

# trim whitespaces
# example: myvar=$(trim "$myvar")
trim() {
    local var="$*"
    # remove leading whitespace characters
    var="${var#"${var%%[![:space:]]*}"}"
    # remove trailing whitespace characters
    var="${var%"${var##*[![:space:]]}"}"   
    echo -n "$var"
}

# replace all shell/environment vars in input variable name
# https://stackoverflow.com/a/9636423
# example: myvar=$(replacevars "myvar")
# note: there is NO dollar ($) sign in "myvar"!
replacevars() {	
	local inputvar="$1"   					# input var
	local inputvarname="$inputvar"   		# name of input var
	local inputvarcont="${!inputvarname}" 	# content of input var	
	for i in _ {a..z} {A..Z}; do
		for shellvar in `eval echo "\\${!$i@}"`; do # shell var (loop for each)
			#echo ">>> $shellvar <<<"
			local shellvarname="$shellvar"   		# name of shell var
			local shellvarcont="${!shellvar}" 			# content of shell var
			if [ "$shellvarname" != "$inputvarname" ]; then	
				local search="{$shellvarname}"					# search for string "{$shellvarname}" (e.g. "{myvar}")
				local replace="$shellvarcont"					# and replace with $shellvarcont
				inputvarcont=${inputvarcont//$search/$replace}	# in $inputvarcont
			fi
		done
	done
	echo "$inputvarcont" # return edited content of input var name
}

#
# CHECKS
#

# # Make sure user is root
# if [ "$(whoami)" != "root" ]; then
#     die "error: call this script with sudo or as root"
# fi

# Check if this is executed on Ubuntu or Debian (to prevent running this on the local OS by accident)
OS_NAME=$(echo "${OS_NAME}" | tr '[:upper:]' '[:lower:]')
if [ "${OS_NAME}" != 'ubuntu' ] && [ "${OS_NAME}" != 'debian' ] && [ $ALLOW_LOCAL = false ]; then
    die "error: this script is only allowed to run on Ubuntu or Debian"
fi

#
# FLOW
#

# Create backups directory
if ! [ -d "$GLOBALBACKUPSDIR" ]; then
    sudo mkdir -p "$GLOBALBACKUPSDIR" || die "error: could not create backups directory"
fi

# Set final backup directory
FINALBACKUPDIR="$GLOBALBACKUPSDIR/$(date +"%Y%m%d%H%M%S")-$SCRIPTALIAS"

# Change to app directory
cd "$SCRIPTDIR" || die "error: could not change to $SCRIPTALIAS directory"

# Stop containers making sure docker-compose.override.yaml is not used
sudo docker compose -f docker-compose.yaml down || die "error: could not stop $SCRIPTALIAS docker container(s)"

# Backup whole app directory (which includes database data in .volumes)
sudo cp -rp "$SCRIPTDIR" "$FINALBACKUPDIR" || die "error: could not backup $SCRIPTALIAS"

# Start app containers making sure docker-compose.override.yaml is not used
sudo docker compose -f docker-compose.yaml up -d || die "error: could not start docker container(s)"

# Done
say "$SCRIPTALIAS successfully backed up"