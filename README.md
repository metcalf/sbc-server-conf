Before an upgrade/reflash
* Search for the previous version/name and replace where needed
* Homeassistant backup?

Installing
* Follow instructions to flash Raspberry Pi OS lite. Before flashing, customize OS settings with the user account password, host name and SSH authorized key. Set timezone to UTC.
* Configure local DHCP to issue a fixed IP for the MAC.
* SSH to the device
* `apt-get update && apt-get upgrade`
*  `reboot`
* Pull secrets from 1Password and update as needed
* Run:
```
ansible-playbook --inventory <IP ADDRESS>, playbook.yml --verbose
```

* Add /home/andrew/.ssh/id_ed25519.pub to Github deploy keys as needed ([bots_n_scrapers](https://github.com/metcalf/bots_n_scrapers/settings/keys))

Once DDNS is setup:
```
ansible-playbook --inventory hosts playbook.yml --verbose
```
Or remotely:
```
ansible-playbook --inventory home-public.itsshedtime.com, playbook.yml --verbose
```

## Client Certificate Authentication with Cloudflare mTLS

Home Assistant (homeassistant.itsshedtime.com) uses two-layer mTLS authentication:
- **Layer 1**: End users authenticate to Cloudflare with Cloudflare-managed client certificates
- **Layer 2**: Cloudflare authenticates to nginx with Authenticated Origin Pulls (using your CA)

To set up:

1. Require a client certificate for the hostname with a Cloudflare mTLS rule

2. Initialize your CA for Authenticated Origin Pulls:
   ```bash
   ./scripts/init-ca.sh
   ```

3. Upload origin certificate to Cloudflare:
   ```bash
   export CLOUDFLARE_ZONE_ID='your-zone-id'
   export CLOUDFLARE_EMAIL='your-email'
   export CLOUDFLARE_API_KEY='your-global-api-key'
   ./scripts/upload-cloudflare-origin-cert.sh homeassistant.itsshedtime.com
   ```

4. Enable Authenticated Origin Pulls:
   ```bash
   ./scripts/enable-cloudflare-origin-pulls.sh homeassistant.itsshedtime.com
   ```
   (uses same environment variables as step 3)

5. Deploy to server:
   ```bash
   ansible-playbook --inventory hosts playbook.yml --verbose
   ```

6. Generate client certificates for your devices:
   ```bash
   ./scripts/generate-cloudflare-client-cert.sh <device-name>
   ```
   (Follow interactive prompts to submit CSR to Cloudflare)

7. Install the `.p12` certificates on your devices

See [CLIENT-CERTS.md](CLIENT-CERTS.md) for detailed instructions.

## Exposing Home Assistant entities to Alexa (Matter)

`home-assistant-matter-hub` runs as the `matter-hub` container (see
`files/homeassistant/compose.yml`) and publishes HA entities to Alexa as a Matter
bridge. Ansible installs and configures the container, but the bridge itself and
its entity list are runtime state stored in matter-hub's own database under
`/var/local/homeassistant/matter-hub/data`, so they are *not* in this repo. A
rebuild reinstalls the container but not the bridge; you would re-create and
re-pair it by hand.

That path is under `/var/local/homeassistant` (mounted as `/config`) on purpose,
so HA's backup sweeps up the bridge and its Matter fabric credentials for free.
`matter-hub.env` is the exception and lives at `/var/local/matter-hub/`: it is
0600 root because it holds the HA token, and HA's backup runs as uid 8123, so
keeping it under `/config` aborts every automatic backup with a `PermissionError`
-- which also breaks the nightly S3 upload, since that looks for a fresh tar.

Web UI: http://192.168.0.203:8482 (LAN only -- it has no authentication of its
own, so ufw restricts 8482 to 192.168.0.0/22).

### Choosing which entities Alexa sees

Apply the `expose-to-alexa` label to entities in Home Assistant (Settings >
Devices & Services > Entities, multi-select, Add label). The "Alexa" bridge
filters on that label.

The filter matches the label *id* (`expose_to_alexa`), not the display name
(`expose-to-alexa`) -- HA slugifies hyphens to underscores when creating a label.
matter-hub accepts either form, and the label id is immutable once created, so
renaming the label in the UI will not break the filter.

To add devices once the bridge is paired:

1. Apply the label in HA.
2. Wait ~60s. matter-hub's refresh adds the bridged endpoint on its own; no
   restart, and no re-pairing -- the bridge stays commissioned permanently.
3. If Alexa does not notice, say "Alexa, discover devices" or use
   Devices > + > Add Device > Discover.

Removing is the messy direction: untagging cleanly removes the endpoint, but
Alexa usually leaves a ghost device stuck as "unresponsive" that has to be
deleted by hand in the Alexa app.

### Pairing

Create the bridge on port **5540** -- Alexa rolls back pairing ~20s in on other
ports. Then pair from the Alexa app.

**Use the 11-digit manual pairing code, not the QR code.** As of Sep 2026 the QR
scan failed repeatedly with "Alexa couldn't find your Matter device" while the
manual code worked on the same Echo. This is backwards from what the payload
implies (the QR encodes `discoveryCaps = on-network only`, the manual code cannot
express that at all), but it is what actually happened. Alexa also shows a
"within 30 feet" BLE-style prompt during setup; ignore it, matter-hub has no
Bluetooth and commissions over IP.

Alexa additionally shows a "not Matter certified" prompt that you must accept.
matter-hub uses development Matter credentials (vendor ID `0xFFF1`, a Matter test
vendor ID). Some Echo models reportedly check attestation against the production
trust store and refuse outright; an Echo Dot on 5GHz accepted it here.

### Debugging discovery

If Alexa cannot find the bridge, check these in order before touching the network
-- a full investigation in Sep 2026 cleared Omada, IGMP snooping, the 2.4/5GHz
split and IPv6 entirely, and the answer was the pairing code:

* `curl -s http://127.0.0.1:8482/api/network` -- matter-hub's own diagnostics.
  All checks should pass and mDNS should be bound to `eth0`.
* `avahi-browse -rpt _matterc._udp` on another LAN host, or `dns-sd -B
  _matterc._udp local` on macOS. Note `dns-sd` output is buffered; redirect to a
  file rather than piping to `head`, or it looks like nothing was found.
* `tcpdump -i eth0 -n "udp port 5540 or udp port 5353"`. A working Echo sends
  `ANY (QM)? _matterc._udp.local` and the bridge answers with the PTR plus SRV,
  TXT and address records. Commissioning then arrives as traffic *to*
  192.168.0.203:5540. Note the `matter-server` container also uses port 5540 as a
  *client* from an ephemeral port, which is easy to mistake for bridge traffic.

Notes:
* Keep it under ~80 devices. Alexa becomes unreliable past roughly 80-100 per
  bridge. Add a second bridge on 5541 rather than growing this one.
* Alexa only ever sends "on" for an exposed `automation`: turning it on calls
  `automation.trigger`, turning it off is a no-op, and its state always reads
  off. `automation.trigger` defaults to `skip_condition: true`, so **the
  automation's conditions are skipped** -- move any condition you rely on as a
  safety check into the action block before exposing it.
* This is unrelated to the `matter-server` container, which is the opposite
  direction (lets HA control Matter devices).

## Logs

VictoriaLogs (`tasks/victorialogs.yml`) keeps a year of logs, capped at 20GiB,
on ExtData. It receives:

* the journal, shipped by `systemd-journal-upload`: systemd units, the kernel,
  anything a cron job sends through `logger`, and the containers, whose log
  driver is journald
* syslog from other devices, which rsyslog forwards as well as writing to
  `/var/log/remote` for the S3 archive

Not in there: services that log to their own files (nginx, mosquitto,
ical-filter-proxy, samba).

The search UI is at `https://home-logs.itsshedtime.com` and at
`http://127.0.0.1:9428/select/vmui/` on the server. Useful queries:

* `SYSLOG_IDENTIFIER:homeassistant error` -- a container or program by name
* `_SYSTEMD_UNIT:nginx.service` -- a systemd unit
* `hostname:crawlspace-th16` -- a device logging over syslog
* `SYSLOG_IDENTIFIER:service_check` -- what the service check found

VictoriaLogs has no login, so Cloudflare's client certificate check is all
that protects the hostname. Set it up in this order, so the hostname never
resolves without the check in front of it:

1. In Cloudflare, add `home-logs.itsshedtime.com` to the mTLS hosts and to
   the WAF rule that blocks requests without a verified client certificate,
   as for Home Assistant (see [CLIENT-CERTS.md](CLIENT-CERTS.md)).
2. Deploy with the playbook. certbot uses a DNS challenge, so this works
   before the hostname exists.
3. Add a proxied DNS record for `home-logs.itsshedtime.com`, matching
   `homeassistant.itsshedtime.com`.
4. Enable Authenticated Origin Pulls for the hostname:
   `./scripts/enable-cloudflare-origin-pulls.sh home-logs.itsshedtime.com`

## Service check

`check_services` runs every 5 minutes and fails its healthchecks.io check when
a systemd unit or container stays down, keeps restarting (3 times in an hour),
or any unit is in the failed state. A single crash that recovers is not
reported. The alert's body lists the problems. A new always-on systemd service
needs adding to `UNITS` in `files/check_services`; containers are picked up
from the compose file.

## Home Assistant MCP server (for Claude)

`ha-mcp` runs as a container (see `files/homeassistant/compose.yml`) so Claude
can read HA state, logs and traces and make UI-style config changes. It runs
on an internal Docker network (no internet or host loopback services; on the
host it reaches HA plus ports ufw already opens to anyone) and is published at
`https://ha-mcp.itsshedtime.com/mcp` through nginx. Three layers sit in front
of it, none of them HA:

1. Cloudflare Access requires a service token, sent as one `Authorization`
   header. nginx strips it before proxying.
2. nginx only accepts Cloudflare's Authenticated Origin Pulls client cert.
3. Only `/mcp` is proxied; everything else on the hostname is a 404.

HA tokens can't be scoped, so the token is admin-equivalent. Riskier tool
modules are left out with `ENABLED_TOOL_MODULES` in the compose file.

Setup:

1. In HA, create a long-lived access token for ha-mcp (profile > Security) and
   add it to `secrets.yml` as `ha_mcp_hass_token`.
2. In Cloudflare, add a proxied DNS record for `ha-mcp.itsshedtime.com`
   pointing at the house, matching `homeassistant.itsshedtime.com`.
3. In Cloudflare Zero Trust, create a service token, then an Access
   application for `ha-mcp.itsshedtime.com` with a single **Service Auth**
   policy that includes only that token. Set the app's
   `read_service_tokens_from_header` to `Authorization` (API only, and the
   only value Cloudflare accepts) so the token travels in one header as
   `{"cf-access-client-id": "<id>", "cf-access-client-secret": "<secret>"}`.
4. Enable Authenticated Origin Pulls for the hostname:
   `./scripts/enable-cloudflare-origin-pulls.sh ha-mcp.itsshedtime.com`
5. Deploy with the playbook.

Clients use the committed `.mcp.json`:

* **Locally**, its `headersHelper` (`scripts/ha-mcp-headers`) builds the
  header from the macOS keychain; the script has the commands to store it.
* **In a Claude Code cloud session**, `headersHelper` doesn't run. Add an API
  credential to a cloud environment dedicated to this repo: allowed website
  `ha-mcp.itsshedtime.com`, custom header `Authorization` with no prefix,
  and the JSON above as the value. Anthropic's proxy attaches it after the
  request leaves the session, so the token never enters it.

To cut off access, delete the Cloudflare service token or revoke the HA token.
