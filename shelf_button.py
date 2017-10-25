import shader_converter
reload(shader_converter)

"""
LieftClick - create new shader, copy parameters and replace old shader
Ctrl + LeftCLick - just create shader and copy parameters (for tests)
"""

if kwargs['ctrlclick']:
    # just convert
    shader_converter.convert()
else:
    # convert and replace
    shader_converter.convert_and_replace()