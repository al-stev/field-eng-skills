#!/usr/bin/env bash
# Sourceable helper for reading/writing credentials in ~/.fe-skills/.env.
# Usage: source scripts/tsm-env.sh; tsm_load KEY; tsm_save KEY VALUE

TSM_ENV="$HOME/.fe-skills/.env"

tsm_load() {   # tsm_load KEY → prints value
    grep "^$1=" "$TSM_ENV" 2>/dev/null | head -1 | cut -d= -f2-
}

tsm_save() {   # tsm_save KEY VALUE → upserts key in .env
    mkdir -p "$(dirname "$TSM_ENV")" && chmod 700 "$(dirname "$TSM_ENV")"
    if grep -q "^$1=" "$TSM_ENV" 2>/dev/null; then
        sed -i '' "s|^$1=.*|$1=$2|" "$TSM_ENV"
    else
        # Ensure file ends with newline before appending
        if [ -s "$TSM_ENV" ] && [ "$(tail -c 1 "$TSM_ENV" | xxd -p)" != "0a" ]; then
            echo "" >> "$TSM_ENV"
        fi
        echo "$1=$2" >> "$TSM_ENV"
    fi
    chmod 600 "$TSM_ENV"
}
