# Git

I'm the only contributor, so commit directly to main. Only create a branch
when there's a specific reason (e.g. a risky or experimental change), and say why.

# Home Assistant

The `home-assistant` MCP server (see README) can change HA config through its
API. Entities, automations and templates defined in `files/homeassistant/`
are owned by this repo and can't be edited through the API; change the YAML
and deploy with Ansible instead.
