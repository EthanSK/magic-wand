"""Classify hard endpoints and exterior assembly air without hiding occupancy.

All permanent carrier/tab intrusions fail. A named disposable helper may
temporarily occupy a hole only when its complete ordered CAD and bead
withdrawal checks pass; the route remains obstructed until cleanup.
"""
def external_air(name):
    return (name.endswith(('_cap_travel','_socket_loading','_soldered_socket_slide','_soldered_socket_dogleg'))
            or name in ('centred OP1 and complete prewired insertion',
                'OP1 prewired plug insertion from below before fitting the rod','OP1 switch insertion',
                'shifted Grove plug operating stroke','shifted Grove lead operating stroke'))

def fixed_endpoints(name,poses):
    if not external_air(name):return poses
    if name.endswith('_cap_travel') or name.startswith('shifted Grove '):
        # Moving cap or top-side DFRobot paddle/lead approach air; the
        # permanent switch cut and the actual hinge bores remain hard.
        return []
    if name in ('centred OP1 and complete prewired insertion','OP1 switch insertion'):
        return poses[:1]  # Full seated hardware at translation zero.
    return poses[-1:]  # Plug and socket insertion terminate at seated pose.
