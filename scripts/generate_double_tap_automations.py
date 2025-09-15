# /// script
# dependencies = [
#   "pyyaml",
# ]
# ///

import os
import yaml

areas = [
    {
        "name": "kitchen",
        "light_entities": [
            "light.2nd_floor_kitchen_downlights",
            "light.2nd_floor_kitchen_island_pendant",
            "light.2nd_floor_kitchen_undercabinet"
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "eat",
            "dim"
        ],
        "trigger_buttons": [
            [
                "button.2nd_floor_kitchen_back_door_position_2_keypad_kitchen_bright",
                "button.2nd_floor_family_room_by_kitchen_position_1_keypad_kitchen_bright",
                "button.2nd_floor_dining_room_kitchen_wall_position_2_keypad_kitchen_bright",
            ],
            [
                "button.2nd_floor_kitchen_back_door_position_2_keypad_ambient",
                "button.2nd_floor_family_room_by_kitchen_position_1_keypad_kitchen_ambient",
                "button.2nd_floor_dining_room_kitchen_wall_position_2_keypad_ambient",
            ],
            [
                "button.2nd_floor_kitchen_back_door_position_2_keypad_morning",
                "button.2nd_floor_family_room_by_kitchen_position_1_keypad_kitchen_eat",
                "button.2nd_floor_dining_room_kitchen_wall_position_2_keypad_morning",
            ],
            [
                "button.2nd_floor_kitchen_back_door_position_2_keypad_eat",
                "button.2nd_floor_family_room_by_kitchen_position_1_keypad_kitchen_dim",
                "button.2nd_floor_dining_room_kitchen_wall_position_2_keypad_eat",
            ],
        ],
        "extra_triggers": [
            [{
                "device_id": "4e26b4960c904eed2cb2201650905ebc",
                "leap_button_number": 1,
            }],
            [{
                "device_id": "4e26b4960c904eed2cb2201650905ebc",
                "leap_button_number": 2,
            }],
            [{
                "device_id": "4e26b4960c904eed2cb2201650905ebc",
                "leap_button_number": 3,
            }],
            [{
                "device_id": "4e26b4960c904eed2cb2201650905ebc",
                "leap_button_number": 4,
            }],
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_kitchen_bright",
            "button.equipment_phantom_position_1_keypad_kitchen_ambient",
            "button.equipment_phantom_position_1_keypad_kitchen_eat",
            "button.equipment_phantom_position_1_keypad_kitchen_dim"
        ]
    },
    {
        "name": "dining",
        "light_entities": [
            "light.2nd_floor_dining_room_chandelier",
            "light.2nd_floor_dining_room_skylight"
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "eat",
            "dim"
        ],
        "trigger_buttons": [
            ["button.2nd_floor_dining_room_kitchen_wall_position_1_keypad_dining_bright"],
            ["button.2nd_floor_dining_room_kitchen_wall_position_1_keypad_dining_ambient"],
            ["button.2nd_floor_dining_room_kitchen_wall_position_1_keypad_dining_dim"],
            ["button.2nd_floor_dining_room_kitchen_wall_position_1_keypad_others_dim"],
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_dining_rm_bright",
            "button.equipment_phantom_position_1_keypad_dining_rm_ambient",
            "button.equipment_phantom_position_1_keypad_dining_rm_eat",
            "button.equipment_phantom_position_1_keypad_dining_rm_dim"
        ]
    },
    {
        "name": "family",
        "light_entities": [
            "light.2nd_floor_family_room_downlights",
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "evening",
            "dim"
        ],
        "trigger_buttons": [
            ["button.2nd_floor_family_room_by_stairs_position_1_keypad_family_bright"],
            ["button.2nd_floor_family_room_by_stairs_position_1_keypad_family_ambient"],
            ["button.2nd_floor_family_room_by_stairs_position_1_keypad_family_dim"],
            ["button.2nd_floor_family_room_by_stairs_position_1_keypad_others_dim"],
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_family_room_bright",
            "button.equipment_phantom_position_1_keypad_family_room_ambien",
            "button.equipment_phantom_position_1_keypad_family_rm_evening",
            "button.equipment_phantom_position_1_keypad_family_room_dim"
        ]
    },
    {
        "name": "living",
        "light_entities": [
            "light.2nd_floor_living_room_chandelier",
            "light.2nd_floor_living_room_downlights"
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "evening",
            "dim"
        ],
        "trigger_buttons": [
            ["button.2nd_floor_living_room_entry_wall_position_1_keypad_bright"],
            ["button.2nd_floor_living_room_entry_wall_position_1_keypad_ambient"],
            ["button.2nd_floor_living_room_entry_wall_position_1_keypad_dim"],
            ["button.2nd_floor_living_room_entry_wall_position_1_keypad_others_dim"],
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_living_rm_bright",
            "button.equipment_phantom_position_1_keypad_living_rm_ambient",
            "button.equipment_phantom_position_1_keypad_living_rm_evening",
            "button.equipment_phantom_position_1_keypad_living_rm_dim"
        ]
    },
    {
        "name": "hall",
        "light_entities": [
            "light.2nd_floor_entry_hall_downlights",
            "light.2nd_floor_entry_hall_vestibule"
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "evening",
            "dim"
        ],
        "trigger_buttons": [
            None,
            None,
            None,
            None,
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_hall_bright",
            "button.equipment_phantom_position_1_keypad_hall_ambient",
            "button.equipment_phantom_position_1_keypad_hall_evening",
            "button.equipment_phantom_position_1_keypad_hall_dim"
        ]
    },
    {
        "name": "lower_stair",
        "light_entities": [
        ],
        "friendly_names": [
            "bright",
            "ambient",
            "evening",
            "dim"
        ],
        "trigger_buttons": [
            None,
            None,
            None,
            None,
        ],
        "action_buttons": [
            "button.equipment_phantom_position_1_keypad_lower_stair_bright",
            "button.equipment_phantom_position_1_keypad_lower_stair_ambien",
            "button.equipment_phantom_position_1_keypad_lower_stair_evenin",
            "button.equipment_phantom_position_1_keypad_lower_stair_dim"
        ]
    }
]

# Collect all the action buttons by row
action_buttons = [[], [], [], []]
for area in areas:
    for i, button in enumerate(area["action_buttons"]):
        action_buttons[i].append(button)


for area in areas:
    for i, name in enumerate(area["friendly_names"]):
        key = f"lutron_double_tap_2f_{area['name']}_{i+1}"


inputs = {}
automations = []

for area in areas:
    for i, name in enumerate(area["friendly_names"]):
        idx = i + 1

        storage_helper = f"lutron_double_tap_2f_{area['name']}_{idx}"
        name = f"Lutron Double Tap - {area['name'].title()} - {idx} ({name.title()})"
        inputs[storage_helper] = {
            "name": name,
            "max": 255
        }

        trigger_buttons = area["trigger_buttons"][i]
        if not trigger_buttons:
            continue

        extra_triggers = []
        if "extra_triggers" in area:
            for trigger in area["extra_triggers"][i]:
                # Aiming for something like:
                #- trigger: event
                #  event_type: lutron_caseta_button_event
                #  event_data:
                #    action: press
                #    type: foo
                extra_triggers.append({
                    "trigger": "event",
                    "event_type": "lutron_caseta_button_event",
                    "event_data": {
                        "action": "press",
                        **trigger
                    }
                })

        automation = {
            "id": f"2f_double_tap_{area['name']}_{idx}",
            "alias": name,
            "description": "",
            "mode": "queued",
            "use_blueprint": {
                "path": "sbc-server-conf/lutron_double_tap.yaml",
                "input": {
                    "button_entities": trigger_buttons,
                    "extra_triggers": extra_triggers,
                    "light_entities": list(area["light_entities"]),
                    "enable_logging": False,
                    "storage_helper": f"input_text.{storage_helper}",
                    "triggered_action": [
                        {
                            "action": "button.press",
                            "target": {
                                "entity_id": [b for b in action_buttons[i] if b != area["action_buttons"][i]]
                            }
                        }
                    ]
                }
            }
        }
        automations.append(automation)

# Write output as formatted Yaml
output = { "input_text": inputs, "automation": automations }
with open(os.path.join("files/homeassistant/packages", "lutron_double_tap.yaml"), "w") as f:
    yaml.dump(output, f)
