'''menuData
act={name:Convert_shader,action:convert()}
'''
from __future__ import absolute_import
import hou
from . import shader
reload(shader)
from .shader import SuperShader


def convert(replace=False):
    """
    Convert selected nodes to a new shaders via super shader
    :param replace: replace existing references to new shader
    :return: new nodes
    """
    nodes = hou.selectedNodes()
    if not nodes:
        return
    errors = []
    new_nodes = []
    new_shader_map = open_new_shader_menu()
    if not new_shader_map:
        return
    for node in nodes:
        proxy_node = None
        node_name = node.name()
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
            proxy_node = ([x for x in node.allSubChildren() if x.type().name() in ['v_fbx']] or [None])[0]
            if not proxy_node:
                errors.append('Cant get Material shader in %s' % parent)
                continue
        if new_shader_map.get('context').lower() == node.type().category().name().lower():
            parent = parent or node.parent()
        else:
            parent = hou.node('/%s' % new_shader_map.get('context', 'shop').lower().replace('vop', 'mat'))
        # super shader 1
        try:
            super_node = SuperShader(proxy_node or node)
        except Exception as e:
            errors.append(str(e))
            continue
        # create
        # super shader 2
        new_shader = parent.createNode(new_shader_type, node_name=node_name+'_new')
        new_shader.moveToGoodPosition()
        try:
            super_new_shader = SuperShader(new_shader)
        except Exception as e:
            errors.append(str(e))
            continue
        # copy
        super_node.copy_parms_to(super_new_shader)
        if replace:
            # for r in refs:
            #     r.set(new_shader.path())
            # node.setName(node_name + '_old')
            node.destroy()
            new_shader.setName(node_name)
            new_shader.setSelected(True, True)
        new_nodes.append(super_new_shader)
    if errors:
        hou.ui.displayMessage('\n'.join(errors), severity=hou.severityType.Warning)
    return new_nodes


def convert_and_replace():
    return convert(True)


def open_new_shader_menu():
    """
    Open menu using QMenu with all maps
    :return: 
    """
    try:
        from PySide.QtGui import QMenu, QAction, QCursor
    except:
        from PySide2.QtGui import QCursor
        from PySide2.QtWidgets import QMenu, QAction
    maps = SuperShader._get_maps()
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
