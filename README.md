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

TODO:
* Install loggly, pagerduty
* Manage loggly agent
* Paging when services crash
* Write or find a UDP logging service
* Ping alerting
