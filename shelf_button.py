import shader_converter
reload(shader_converter)

"""
LieftClick - create new shader, copy parameters and replace references
Ctrl + LeftCLick - Just Create and Copy parameters (for tests)
"""

if kwargs['ctrlclick']:
    # just convert
    shader_converter.convert()
else:
    # convert and replace
    shader_converter.convert_and_replace()