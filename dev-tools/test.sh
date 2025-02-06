#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2024 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Automates setup and testing

# RED='\033[0;31m'
GREEN='\033[0;32m'
# ORANGE='\033[0;33m'
# BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color
HELP_DIR=./helper

export HELP_DIR='helper'
export DJANGO_SETTINGS_MODULE=embark.settings.dev
export EMBARK_DEBUG=True
export PIPENV_VENV_IN_PROJECT="True"

cleaner() {
  if [[ -f ./embark/embark.log ]]; then
    rm ./embark/embark.log -f
  fi
  
  # killall -9 -q "*daphne*"
  docker container stop embark_db
  docker container stop embark_redis

  docker container prune -f --filter "label=flag"

  fuser -k "${PORT}"/tcp
  exit 1
}

import_helper()
{
  local HELPERS=()
  local HELPER_COUNT=0
  local HELPER_FILE=""
  mapfile -d '' HELPERS < <(find "${HELP_DIR}" -iname "helper_embark_*.sh" -print0 2> /dev/null)
  for HELPER_FILE in "${HELPERS[@]}" ; do
    if ( file "${HELPER_FILE}" | grep -q "shell script" ) && ! [[ "${HELPER_FILE}" =~ \ |\' ]] ; then
      # https://github.com/koalaman/shellcheck/wiki/SC1090
      # shellcheck source=/dev/null
      source "${HELPER_FILE}"
      (( HELPER_COUNT+=1 ))
    fi
  done
  echo -e "\\n""==> ""${GREEN}""Imported ""${HELPER_COUNT}"" necessary files""${NC}\\n"
}

set -a
trap cleaner INT

cd "$(dirname "${0}")" || exit 1
cd .. || exit 1
import_helper
echo -e "\n${GREEN}""${BOLD}""Configuring Embark""${NC}"

# shellcheck disable=SC1091
# source ./.venv/bin/activate || exit 1

sync_emba_forward
exit 0