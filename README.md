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

TODO:
* Install loggly, pagerduty
* Manage loggly agent
* Paging when services crash
* Write or find a UDP logging service
* Ping alerting
