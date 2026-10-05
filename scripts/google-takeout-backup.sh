#!/bin/bash
set -euo pipefail

# Rotate the Google Takeout archive on the misc share and copy in a new one
# from ~/Downloads. Unlocks Misc first (asking for its passphrase) and locks it
# again at the end, whether or not the copy finished. Safe to rerun after an
# interruption: it picks up the rotation or the copy where it stopped.

HOST=home-sbc-server-local.itsshedtime.com
SHARE_URL="smb://andrew@HOMESERVER._smb._tcp.local/misc"
MNT=/Volumes/misc
ARCHIVE="$MNT/google archive"
PREV="$ARCHIVE/previous"
# Holds the old previous while the current archive moves into previous, so an
# interrupted rotation never leaves us with only half of either.
PREV_OLD="$ARCHIVE/previous.old"
COPY_ATTEMPTS=5

# Without macOS's Files and Folders permission the glob below silently
# matches nothing, so check for that first.
if ! ls ~/Downloads >/dev/null 2>&1; then
    echo "ERROR: can't read ~/Downloads. Give this terminal app access in System Settings >" >&2
    echo "Privacy & Security > Files & Folders (Downloads and Network Volumes)." >&2
    exit 1
fi

shopt -s nullglob
takeouts=(~/Downloads/takeout*)
if [ ${#takeouts[@]} -eq 0 ]; then
    echo "ERROR: no takeout* files in ~/Downloads" >&2
    exit 1
fi
echo "Takeout files to copy:"
ls -lh "${takeouts[@]}"

# Homebrew's rsync; macOS's own doesn't support --append-verify.
RSYNC=/opt/homebrew/bin/rsync
[ -x "$RSYNC" ] || { echo "ERROR: brew install rsync" >&2; exit 1; }

mount_share() {
    [ -d "$ARCHIVE" ] && return
    # A mount left over from before Misc was locked goes stale.
    if mount | grep -q " on $MNT "; then
        umount -f "$MNT" || true
    fi
    osascript -e "mount volume \"$SHARE_URL\"" >/dev/null
    if [ ! -d "$ARCHIVE" ]; then
        echo "ERROR: $ARCHIVE not found after mounting the share" >&2
        exit 1
    fi
}

lock_misc() {
    echo
    echo "Locking Misc..."
    if mount | grep -q " on $MNT "; then
        diskutil unmount "$MNT" >/dev/null || umount -f "$MNT" || true
    fi
    if ssh -t "$HOST" sudo systemctl stop systemd-cryptsetup@ExternalMisc_crypt.service; then
        echo "Misc locked."
    else
        echo "WARNING: failed to lock Misc. Run on the server:" >&2
        echo "  sudo systemctl stop systemd-cryptsetup@ExternalMisc_crypt.service" >&2
    fi
}

echo
echo "Unlocking Misc (sudo password, then the Misc passphrase)..."
ssh -t "$HOST" sudo systemctl start mnt-ExternalMisc.mount
trap lock_misc EXIT

mount_share

# Move everything in the archive except previous/ (and previous.old/) into previous/.
move_current_to_prev() {
    find "$ARCHIVE" -mindepth 1 -maxdepth 1 ! -name previous ! -name previous.old \
        -exec mv {} "$PREV/" \;
}

already_copying=false
for f in "${takeouts[@]}"; do
    if [ -e "$ARCHIVE/$(basename "$f")" ]; then
        already_copying=true
    fi
done

if [ -d "$PREV_OLD" ]; then
    echo "Finishing an interrupted rotation..."
    move_current_to_prev
    rm -rf "$PREV_OLD"
elif $already_copying; then
    echo "This Takeout is already partly copied; skipping the rotation."
else
    echo "Rotating: deleting previous/ and moving the current archive into it..."
    if [ -d "$PREV" ]; then
        mv "$PREV" "$PREV_OLD"
    fi
    mkdir "$PREV"
    move_current_to_prev
    rm -rf "$PREV_OLD"
fi

# --partial keeps an interrupted file and --append-verify resumes it on the
# next attempt (resending the whole file if the checksum doesn't match).
# Files already copied in full are skipped.
attempt=1
until "$RSYNC" -t --partial --append-verify --progress "${takeouts[@]}" "$ARCHIVE/"; do
    status=$?
    # 20: interrupted with Ctrl-C, so stop rather than retry.
    if [ $status -eq 20 ] || [ $attempt -ge $COPY_ATTEMPTS ]; then
        echo "ERROR: copy failed (rsync exit $status). Rerun the script to resume." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    echo "Copy failed (rsync exit $status); retrying ($attempt/$COPY_ATTEMPTS) in 10s..."
    sleep 10
    mount_share
done

echo
echo "Copied. Archive now holds:"
ls -lh "$ARCHIVE"
