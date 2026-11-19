"""Set the native smooth-timelapse tower's anchored ribs and separate bed footprint."""
import json


def add_tower_base(files, position, brim_mm, extra_rib_mm):
    key = 'Metadata/project_settings.config'
    settings = json.loads(files[key])
    # Ethan calls this the "viewing pipe". Only the disposable tower and its
    # own base should fuse permanently. The live camera is independent of it.
    settings.update(prime_tower_enable_framework='1', prime_tower_rib_wall='1',
                    prime_tower_rib_width='14', prime_tower_extra_rib_length=str(extra_rib_mm),
                    prime_tower_max_speed='30', prime_tower_brim_width=str(brim_mm),
                    wipe_tower_x=[str(position[0])], wipe_tower_y=[str(position[1])])
    assert settings['enable_prime_tower'] == settings['timelapse_type'] == '1'
    files[key] = json.dumps(settings, indent=2).encode()
