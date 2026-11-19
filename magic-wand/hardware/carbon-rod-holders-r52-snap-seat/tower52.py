"""Place the smooth-timelapse prime tower on its own wide deposited brim."""
import json


def add_tower_base(files, position, brim_mm=25):
    key = 'Metadata/project_settings.config'
    settings = json.loads(files[key])
    # The native tower had only a 3 mm brim when it detached from the sheet.
    settings['prime_tower_brim_width'] = str(brim_mm)
    settings['wipe_tower_x'] = [str(position[0])]
    settings['wipe_tower_y'] = [str(position[1])]
    assert settings['enable_prime_tower'] == settings['timelapse_type'] == '1'
    files[key] = json.dumps(settings, indent=2).encode()
