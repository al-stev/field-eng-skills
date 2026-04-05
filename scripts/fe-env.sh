#!/usr/bin/env bash
# Sourceable helper for reading/writing credentials in ~/.fe-skills/.env.
# Usage: source scripts/fe-env.sh; fe_load KEY; fe_save KEY VALUE

FE_ENV="$HOME/.fe-skills/.env"

fe_load() {   # fe_load KEY → prints value
    grep "^$1=" "$FE_ENV" 2>/dev/null | head -1 | cut -d= -f2-
}

fe_save() {   # fe_save KEY VALUE → upserts key in .env
    mkdir -p "$(dirname "$FE_ENV")" && chmod 700 "$(dirname "$FE_ENV")"
    if grep -q "^$1=" "$FE_ENV" 2>/dev/null; then
        sed -i '' "s|^$1=.*|$1=$2|" "$FE_ENV"
    else
        # Ensure file ends with newline before appending
        if [ -s "$FE_ENV" ] && [ "$(tail -c 1 "$FE_ENV" | xxd -p)" != "0a" ]; then
            echo "" >> "$FE_ENV"
        fi
        echo "$1=$2" >> "$FE_ENV"
    fi
    chmod 600 "$FE_ENV"
}
