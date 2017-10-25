"""
Function for Houdini FBX material. Get layer map on FBX Surface Shader (v_fbx) be parameter name.
"""


def remap_parm(node, parm_name, get_value=True):
    # find apply# parameter
    apply_remap = {
        'diffuse_map': 'd',
        'diffuse_weight': 'df',
        'ambient_map': 'a',
        'ambient_weight_map': 'af',
        'opacity_map': 'o',
        'opacity_weight': 'of',
        'specular_map': 's',        # maybe r?
        'specular_weight': 'sf',       # maybe rf?
        'emission_color': 'ems',
        'emission_map': 'emsf',
        'specular_roughness': 'shn',
        'bump_map': 'bump',
        }
    if get_value:
        # get_value
        if parm_name not in apply_remap:
            return
        # search apply in right state
        for i in range(1, 17):
            p = node.parm('apply%s' % i)
            if p:
                if p.eval() == apply_remap.get(parm_name):
                    return node.parm('map%s' % i).eval()
    else:
        print 'Not implement'
        return False
        # return True if value is set
