* Assign a fixed IP (possibly from the DHCP server)
* Copy SSH public key to device (`ssh-copy-id <public key> andrew@192.168.1.141`)
* Use SSH agent forwarding when connecting for access to Github (`ssh -A andrew@192.168.1.141`)
* Install Ansible
* Run:
```
ansible-playbook --ask-become-pass -i hosts playbook.yml --connection=local
```


TODO:
* Install node, typescript, ts-node, loggly, pagerduty
* Manage starting services with systemd
* Set up log rotation
* Manage loggly agent
* Paging when services crash
