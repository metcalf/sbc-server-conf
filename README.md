Before an upgrade/reflash
* Consider using a new SD card so the old one acts as a backup and to avoid worrying about wear
* Archive /etc/letsencrypt to restore certs without reissuing.
* Search for the previous version/name and replace where needed
* Homeassistant backup?

Installing
* Follow instructions to install Armbian (https://docs.armbian.com/User-Guide_Getting-Started/)
* Determine the IP address
* SSH for the first time to configure passwords
* Copy SSH public key to device
  ```
    ssh-copy-id -i ~/.ssh/id_ed25519.pub andrew@192.168.1.141
    ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.141
  ```
* `apt-get update && apt-get upgrade`
*  `reboot`
* `mv secrets.yml.tmpl secrets.yml` and fill out as needed
* Run:
```
ansible-playbook --inventory hosts playbook.yml --verbose
```
Or remotely:
```
ansible-playbook --inventory home-public.itsshedtime.com, playbook.yml --verbose
```

TODO:
* Install loggly, pagerduty
* Manage starting services with systemd?
* Set up log rotation
* Manage loggly agent
* Paging when services crash
* Write or find a UDP logging service
* Ping alerting
