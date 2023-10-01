import json
import os
import sys
from collections import namedtuple

import requests

# API schema:
# https://github.com/simbaja/milasdk/blob/master/milasdk/gql/mila_schema.gql

LOGIN_PROVIDER = "https://id.milacares.com"
TOKEN_PATH = "/auth/realms/prod/protocol/openid-connect/token"
API_BASE = "https://api.milacares.com/mms"
CLIENT_ID = "prod-ui"

AUTH_PATH = "/tmp/mila_auth"

Appliance = namedtuple("Appliance", ['id', 'room_id', 'mode', 'aqi', 'fanSpeed'])

def request_auth(grant_type, **kwargs):
    resp = requests.post(
        url=LOGIN_PROVIDER + TOKEN_PATH,
        data={
            "grant_type": grant_type,
            "client_id": CLIENT_ID,
            **kwargs
        },
        allow_redirects=False
    )
    resp.raise_for_status()

    result = resp.json()
    return {
        "access_token": result['access_token'],
        "refresh_token": result['refresh_token']
    }


def get_refreshed_token(refresh_token):
    print("Refreshing token")
    return request_auth("refresh_token", refresh_token=refresh_token)

def get_new_access_token(username, password):
    print("Getting new token")
    return request_auth("password", username=username, password=password)

def refresh_or_get_auth(refresh_token, username, password):
    try:
        return get_refreshed_token(refresh_token)
    except requests.HTTPError:
        return get_new_access_token(username, password)

def make_api_request(auth, query):
    resp = requests.post(
        url="https://api.milacares.com/graphql",
        headers={
            "Authorization": "Bearer %s" % auth['access_token'],
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "query": query
        })
    )
    resp.raise_for_status()

    result = resp.json()
    if "errors" in result:
        raise result["errors"][0]['message']

    return result['data']

def get_appliance(auth):
    data = make_api_request(auth, """{
                     owner {
                        appliances {
                            id
                            room { id }
                            state { actualMode }
                            sensors(kinds: [Aqi, FanSpeed]) {
                                    kind
                                    latest(precision: {value: 1, unit: Minute}) {
                                      instant
                                      value
                                    }
                                  }
                        }
                    }
                }""")

    appliance = data['owner']['appliances'][0]

    sensor_data = {}
    for sensor in appliance['sensors']:
        sensor_data[sensor['kind']] = sensor['latest']['value']

    return Appliance(
        appliance['id'],
        appliance['room']['id'],
        appliance['state']['actualMode'],
        sensor_data['Aqi'],
        sensor_data['FanSpeed']
    )

def get_sensor(auth, appliance_id, sensor_name):
    data = make_api_request(auth, """{
                            owner {
                                appliance(applianceId: "%s") {
                                  sensor(kind: %s) {
                                    kind
                                    latest(precision: {value: 1, unit: Minute}) {
                                      instant
                                      value
                                    }
                                  }
                                }
                            }
                        }""" % (appliance_id, sensor_name))
    return data['owner']['appliance']['sensor']['latest']['value']

def set_automagic_mode(auth, room_id):
    make_api_request(auth, """mutation {
                       applyRoomAutomagicMode(roomId: %s) { id }
                     }""" % room_id)

def set_quiet_mode(auth, appliance_id):
    make_api_request(auth, """mutation {
                        applyQuietMode(applianceId: "%s", isEnabled: true) {
                            id
                        }
                     }
                     """ % appliance_id)

def set_manual_mode(auth, room_id, fan_speed, target_aqi):
    if fan_speed is None:
        # 0 means lowest speed, "null" means off
        fan_speed = "null"
    else:
        fan_speed = "%d" % fan_speed

    make_api_request(auth, """mutation {
                        applyRoomManualMode(roomId: %s, fanSpeed: %s, targetAqi: %d) { id }
                     }""" % (room_id, fan_speed, target_aqi))

def try_get_appliance(auth):
    try:
        return get_appliance(auth)
    except requests.HTTPError as e:
        if e.response.status_code in [401, 403]:
            return None
        else:
            raise

def read_auth():
    if os.path.isfile(AUTH_PATH):
        with open(AUTH_PATH, encoding="utf-8") as f:
            return json.load(f)

    return None

def write_auth(auth):
    with open(AUTH_PATH, 'w', encoding="utf-8") as f:
        json.dump(auth, f)

def read_or_get_access(username, password):
    auth = read_auth()
    got_new_auth = False

    if auth is None:
        got_new_auth = True
        auth = get_new_access_token(username, password)

    appliance = try_get_appliance(auth)
    if appliance is None:
        # Fetch a new token if we haven't already
        if not got_new_auth:
            got_new_auth = True
            auth = refresh_or_get_auth(auth['refresh_token'], username, password)
            appliance = try_get_appliance(auth)

        if appliance is None:
            raise "Could not fetch device info"

    if got_new_auth:
        write_auth(auth)

    return auth, appliance

def poll():
    username, password = sys.argv[1:]
    auth, appliance = read_or_get_access(username, password)

    if appliance.mode == "Manual":
        if appliance.fanSpeed > 100:
            msg = "Leaving in manual mode because speed > 100"
        elif appliance.aqi < 70:
            msg = "Leaving in manual mode because AQI isn't high"
        else:
            msg = "Switching to automagic mode"
            set_automagic_mode(auth, appliance.room_id)
            set_quiet_mode(auth, appliance.id)
    elif appliance.mode not in ['PowerSaver', 'Quarantine', 'WhiteNoise']:
        if appliance.aqi < 50:
            msg = "Switching off"
            set_manual_mode(auth, appliance.room_id, None, 50)
        else:
            msg = "Leaving on %s" % appliance.mode
    else:
        msg = "Not doing anything in mode %s" % appliance.mode

    print(msg + " (aqi: %d)" % appliance.aqi)


poll()
