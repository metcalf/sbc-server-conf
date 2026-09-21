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

1. Configure Cloudflare Access application with mTLS (generates user certificates)

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

TODO:
* Install loggly, pagerduty
* Manage loggly agent
* Paging when services crash
* Write or find a UDP logging service
* Ping alerting
