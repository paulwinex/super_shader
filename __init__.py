'''menuData
act={name:Convert_shader,action:convert()}
'''
import hou
import super_shader
reload(super_shader)


def convert(replace=False):
    nodes = hou.selectedNodes()
    if not nodes:
        return
    errors = []
    new_nodes = []
    new_shader_map = open_new_shader_menu()
    if not new_shader_map:
        return
    for node in nodes:
        new_shader_type = new_shader_map.get('op_name')
        if node.type().name() == new_shader_type:
            errors.append('Duplicate node type for %s' % node.name())
            continue

        # get parent
        refs = node.parmsReferencingThis()
        parent = None
        if node.type().name() == 'material':
            # it is FBX subnet?
            parent = node.parent()
            node = ([x for x in node.allSubChildren() if x.type().name() in ['v_fbx']] or [None])[0]
            if not node:
                errors.append('Cant get Material shader in %s' % parent)
                continue
        if new_shader_map.get('context').lower() == node.type().category().name().lower():
            parent = parent or node.parent()
        else:
            parent = hou.node('/%s' % new_shader_map.get('context', 'shop').lower().replace('vop', 'mat'))
        # super shader 1
        try:
            super_node = super_shader.SuperShader(node)
        except Exception as e:
            errors.append(str(e))
            continue
        # create
        # super shader 2
        new_shader = parent.createNode(new_shader_type, node_name=node.name()+'_new')
        try:
            super_new_shader = super_shader.SuperShader(new_shader)
        except Exception as e:
            errors.append(str(e))
            continue
        # copy
        super_node.copy_parms_to(super_new_shader)
        if replace:
            for r in refs:
                r.set(new_shader.path())
        new_nodes.append(super_new_shader)
    if errors:
        hou.ui.displayMessage('\n'.join(errors), severity=hou.severityType.Warning)
    return new_nodes


def convert_and_replace():
    return convert(True)


def open_new_shader_menu():
    try:
        from PySide.QtGui import QMenu, QAction, QCursor
    except:
        from PySide2.QtGui import QCursor
        from PySide2.QtWidgets import QMenu, QAction
    maps = super_shader.SuperShader._get_maps()
    if not maps:
        return
    menu = QMenu(hou.ui.mainQtWindow())
    menu.setStyleSheet(hou.ui.qtStyleSheet())
    for m in maps:
        menu.addAction(QAction(m['name'], menu))
    act = menu.exec_(QCursor.pos())
    if not act:
        return
    new_shader_map = ([x for x in maps if x['name'] == act.text()] or [None])[0]
    return new_shader_map
