entity_ids = data.get('entity_ids')
devices = data.get('devices')
helper = data.get('helper')
timeout_seconds = data.get('timeout_seconds')

title='Last Seen Monitor'

def error(text, raise_exception = True):
    text = 'failure: ' + text
    if helper_state.state != text:
        service_data= {
            'title': title,
            'message': text,
        }
        hass.services.call("notify", "persistent_notification", service_data, blocking=False)
        hass.states.set(helper, text, helper_state.attributes)
    if raise_exception:
        raise Exception(text)

assert(helper)
helper_state = hass.states.get(helper)
assert(helper_state.attributes['editable'] == True)
assert(helper_state.attributes['min'] == 0)
assert(helper_state.attributes['pattern'] is None)
assert(helper_state.attributes['mode'] == 'text')
len_max = helper_state.attributes['max']
assert(len_max >= 100)

if entity_ids:
    for entity_id in entity_ids:
        if not hass.states.get(entity_id):
            error('entity_id not found')

if timeout_seconds <= 0:
    error('invalid timeout_seconds')

try:
    helper_update = False
    last_offline = set(helper_state.state.split())

    def check_device(device, now, helper_update, entity_id):
        available = device['available']
        last_seen = device['last_seen']
        if not last_seen:
            available = False
        else:
            if now is None:
                now = dt_util.as_timestamp(dt_util.now())
            if now - dt_util.as_timestamp(last_seen) > timeout_seconds:
                available = False
        if not available and entity_id not in last_offline:
            friendly_name = hass.states.get(entity_id).attributes['friendly_name']
            service_data= {
                'title': title,
                'message': f'Offline: {friendly_name} - {entity_id}',
            }
            hass.services.call("notify", "persistent_notification", service_data, blocking=False)
            logger.warning(f'Offline {friendly_name} - { entity_id }')
            last_offline.add(entity_id)
            helper_update = True
        elif available and entity_id in last_offline:
            last_offline.remove(entity_id)
            helper_update = True
        logger.debug(f'{entity_id}, {hass.states.get(entity_id).attributes["friendly_name"]}, {available}, {last_seen}')
        return now, helper_update

    now = None
    if entity_ids:
        for entity_id in set(entity_ids):
            for device in devices:
                if entity_id in (x['entity_id'] for x in device['entities']):
                    now, helper_update = check_device(device, now, helper_update, entity_id)
                    break
            else:
                error('entity_id not found')
    else:
        for device in devices:
            if device['power_source'] == 'Mains':
                entities = device['entities']
                if not entities:
                    continue
                entities = (x['entity_id'] for x in device['entities'])
                entity_id = sorted(entities, key=lambda x: len(x))[0]
                now, helper_update = check_device(device, now, helper_update, entity_id)
except:
    error('exception', raise_exception = False)
    raise
finally:
    for offline in last_offline.copy():
        if not hass.states.get(offline):
            last_offline.discard(offline)
            helper_update = True
    if helper_update:
        new_offline = ' '.join(last_offline)
        if len(new_offline) > len_max:
            logger.warning('too long offline string, truncating')
            new_offline = new_offline[:len_max]
        hass.states.set(helper, new_offline, helper_state.attributes)