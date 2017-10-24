import shader_converter
reload(shader_converter)

if kwargs['ctrlclick']:
    # just convert
    shader_converter.convert()
else:
    # convert and replace
    shader_converter.convert_and_replace()