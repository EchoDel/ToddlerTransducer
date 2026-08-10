#!/usr/bin/env bash
#
# Install script for the ToddlerTransducer.
#
# Clones the repository, installs the dependencies (VLC, poetry, python
# packages), sets up the systemd service and enables automatic OTA updates.
#
# Usage (fresh Raspberry Pi):
#   curl -sSL https://raw.githubusercontent.com/EchoDel/ToddlerTransducer/main/install/install.sh | bash
#
# Or from an existing checkout:
#   bash install/install.sh
#
# Environment overrides:
#   TT_REPO_URL      Git URL to clone (default: the GitHub repo)
#   TT_INSTALL_DIR   Directory to clone into (default: $HOME/ToddlerTransducer)
#   TT_USER          User to install for when running as root (default: $SUDO_USER)
#   TT_SKIP_SERVICE  Set to 1 to skip the systemd service setup
#   TT_SKIP_OTA      Set to 1 to skip the automatic update setup

set -euo pipefail

REPO_URL="${TT_REPO_URL:-https://github.com/EchoDel/ToddlerTransducer.git}"

# ---------------------------------------------------------------------------
# Work out which user this is being installed for (normally the 'pi' user).
# The script must not run the app as root, so refuse to install for root.
# ---------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
    TARGET_USER="${TT_USER:-${SUDO_USER:-}}"
    if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
        echo "error: refusing to install for the root user." >&2
        echo "       Run this script as a normal user (e.g. 'pi'), or set TT_USER=pi." >&2
        exit 1
    fi
else
    TARGET_USER="$(id -un)"
fi
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

INSTALL_DIR="${TT_INSTALL_DIR:-$TARGET_HOME/ToddlerTransducer}"
POETRY_BIN="$TARGET_HOME/.local/bin/poetry"

echo ">> Installing ToddlerTransducer for user '$TARGET_USER' into '$INSTALL_DIR'"

# Run a command as the target user (only needed when this script is run as root).
as_user() {
    if [ "$(id -u)" -eq 0 ]; then
        sudo -u "$TARGET_USER" env HOME="$TARGET_HOME" "$@"
    else
        env HOME="$TARGET_HOME" "$@"
    fi
}

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
echo ">> Installing system packages (vlc, git, python, ...)"
sudo apt-get update
sudo apt-get install -y vlc git curl python3 python3-pip python3-venv git-lfs

# ---------------------------------------------------------------------------
# 2. Poetry
# ---------------------------------------------------------------------------
if [ ! -x "$POETRY_BIN" ]; then
    echo ">> Installing poetry"
    as_user bash -c "curl -sSL https://install.python-poetry.org | python3 - --yes"
fi

# ---------------------------------------------------------------------------
# 3. Clone the repository
# ---------------------------------------------------------------------------
if [ -d "$INSTALL_DIR/.git" ]; then
    echo ">> Repository already present at $INSTALL_DIR, pulling latest changes"
    as_user git -C "$INSTALL_DIR" pull --ff-only || true
else
    if [ -d "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]; then
        echo "error: $INSTALL_DIR already exists and is not empty." >&2
        exit 1
    fi
    echo ">> Cloning repository from $REPO_URL"
    as_user git clone --recurse-submodules "$REPO_URL" "$INSTALL_DIR"
fi
as_user git -C "$INSTALL_DIR" lfs install --local
as_user git -C "$INSTALL_DIR" lfs pull || true
as_user git -C "$INSTALL_DIR" submodule update --init --recursive

# ---------------------------------------------------------------------------
# 4. Enable SPI (needed for the RFID reader)
# ---------------------------------------------------------------------------
echo ">> Enabling the SPI interface"
if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_spi 0
else
    for CONF in /boot/firmware/config.txt /boot/config.txt; do
        if [ -e "$CONF" ]; then
            sudo sed -i '/^dtparam=spi=/d' "$CONF"
            echo "dtparam=spi=on" | sudo tee -a "$CONF" >/dev/null
            echo ">> Added 'dtparam=spi=on' to $CONF"
            break
        fi
    done
fi

# ---------------------------------------------------------------------------
# 5. Install the python dependencies with poetry
# ---------------------------------------------------------------------------
echo ">> Installing python dependencies with poetry"
as_user bash -c "cd '$INSTALL_DIR' && '$POETRY_BIN' install --with deployment"

# ---------------------------------------------------------------------------
# 6. systemd service
# ---------------------------------------------------------------------------
if [ "${TT_SKIP_SERVICE:-0}" != "1" ]; then
    echo ">> Setting up the ToddlerTransducer systemd service"
    sudo sed -e "s/^User=.*/User=$TARGET_USER/" \
             -e "s|%h/ToddlerTransducer|$INSTALL_DIR|" \
         "$INSTALL_DIR/install/ToddlerTransducer.service" > /tmp/ToddlerTransducer.service
    sudo cp /tmp/ToddlerTransducer.service /etc/systemd/system/ToddlerTransducer.service
    rm -f /tmp/ToddlerTransducer.service
    sudo systemctl daemon-reload
    sudo systemctl enable ToddlerTransducer.service
    sudo systemctl restart ToddlerTransducer.service
fi

# ---------------------------------------------------------------------------
# 7. Automatic updates (cron every 5 minutes + passwordless systemctl)
# ---------------------------------------------------------------------------
if [ "${TT_SKIP_OTA:-0}" != "1" ]; then
    echo ">> Setting up automatic updates"

    # The ota_update.sh cron job needs to stop/start the service without a
    # password prompt, so grant the target user that single permission.
    SYSTEMCTL="$(command -v systemctl)"
    echo "$TARGET_USER ALL=(ALL) NOPASSWD: $SYSTEMCTL stop ToddlerTransducer.service, $SYSTEMCTL start ToddlerTransducer.service, $SYSTEMCTL restart ToddlerTransducer.service" \
        | sudo tee /etc/sudoers.d/toddler-transducer >/dev/null
    sudo chmod 0440 /etc/sudoers.d/toddler-transducer

    CRON_LINE="*/5 * * * * $INSTALL_DIR/install/ota_update.sh"
    if [ "$(id -u)" -eq 0 ]; then
        EXISTING_CRON="$(crontab -u "$TARGET_USER" -l 2>/dev/null || true)"
        if printf '%s\n' "$EXISTING_CRON" | grep -q "ota_update.sh"; then
            echo ">> Cron entry already present"
        else
            printf '%s\n%s\n' "$EXISTING_CRON" "$CRON_LINE" | crontab -u "$TARGET_USER" -
            echo ">> Added cron entry: $CRON_LINE"
        fi
    else
        EXISTING_CRON="$(crontab -l 2>/dev/null || true)"
        if printf '%s\n' "$EXISTING_CRON" | grep -q "ota_update.sh"; then
            echo ">> Cron entry already present"
        else
            printf '%s\n%s\n' "$EXISTING_CRON" "$CRON_LINE" | crontab -
            echo ">> Added cron entry: $CRON_LINE"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo ">> Install complete."
if [ "${TT_SKIP_SERVICE:-0}" != "1" ]; then
    sudo systemctl status ToddlerTransducer.service --no-pager || true
fi
echo ""
echo ">> If the SPI interface was just enabled, reboot for it to take effect:"
echo "   sudo reboot"
