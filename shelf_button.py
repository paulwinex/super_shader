import super_shader
reload(super_shader)

"""
LieftClick - create new shader, copy parameters and replace old shader
Ctrl + LeftCLick - just create shader and copy parameters (for tests)
"""

if kwargs['ctrlclick']:
    # just convert
    super_shader.convert()
else:
    # convert and replace
    super_shader.convert_and_replace()