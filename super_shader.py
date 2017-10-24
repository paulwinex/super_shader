import hou
import os, re, json
import imp
import logging as _logging
logger = _logging.getLogger(__name__)


class SuperShader(object):
    class Parm(object):
        def __init__(self, parm_name, get_callback, set_callback):
            self.name = parm_name
            self._get_callback = get_callback
            self._set_callback = set_callback

        def eval(self):
            return self._get_callback(self.name)

        def get(self):
            return self.eval()

        def set(self, value):
            self._set_callback(self.name, value)

    def __init__(self, node):
        self._node = node
        if False:
            self._node = hou.node('')
        self.__maps = self._get_maps()
        if not self.__maps:
            raise Exception('Map files not found')
        self.op_name = self._node.type().name()
        self._map = None
        for m in self.__maps:
            if m.get('op_name') == self.op_name:
                self._map = m
                break
        else:
            raise Exception('Node type %s not found in maps' % self.op_name)
        self._super_map = self._get_super_map()

    def parm(self, node_parm_name):
        if node_parm_name in self._map['parameters_map']:
            return self.Parm(node_parm_name, self.__get_parm_value, self.__set_parm_value)

    def __get_parm_value(self, super_name):
        if super_name in self._map['parameters_map']:
            node_parm_name = self._map['parameters_map'].get(super_name)
            if not node_parm_name:
                return self._apply_expression(self._super_map_default(super_name), super_name, False)
            m = re.match(r"^:(\w+)\|\|(\w+)$", node_parm_name)
            if m:
                return self._apply_expression(self._get_from_method_or_default(m.group(1), super_name, m.group(2)), super_name, False)
            m = re.match(r"^:(\w+)$", node_parm_name)
            if m:
                return self._apply_expression(self._get_from_method_or_default(m.group(1), super_name), super_name, False)
            return self._apply_expression(self._get_from_node_parameter(node_parm_name, super_name), super_name, False)
        else:
            return self._apply_expression(self._super_map_default(super_name), super_name, False)

    def __set_parm_value(self, super_name, value):
        if super_name in self._map['parameters_map']:
            node_parm_name = self._map['parameters_map'].get(super_name)
            if not node_parm_name:
                return False
            m = re.match(r"^:(\w+)\|\|(\w+)$", node_parm_name)
            if m:
                v = self._get_from_method_or_default(m.group(1), super_name, m.group(2), get_value=False)
                return self.__set_node_value(m.group(2), v, super_name)
            m = re.match(r"^:(\w+)$", node_parm_name)
            if m:
                method = self._load_method(m.group(1))
                if method:
                    return method(self._node, super_name, False)
            return self.__set_node_value(node_parm_name, value, super_name)
        return False

    def __set_node_value(self, parm_name, value, super_name):
        p = self._node.parm(parm_name)
        if p:
            p.set(self._apply_expression(value, super_name))
            return True
        else:
            p = self._node.parmTuple(parm_name)
            if p:
                r = self._apply_expression(value, super_name)
                print '%s > %s' % (super_name, r)
                p.set(hou.Vector3(*r))
                return True
        return False

    def _apply_expression(self, value, super_parm_name, set_value=True):
        expr = self._map.get('set_value_expr' if set_value else 'get_value_expr', {}).get(super_parm_name)
        if expr:
            value = eval(expr.replace('$value', str(value)))
        return value

    def _get_from_method_or_default(self, method, super_parm, default_parm=None, get_value=True):
        m = self._load_method(method)
        res = m(self._node, super_parm, get_value)
        if res is None:
            if default_parm:
                return self._get_from_node_parameter(default_parm, super_parm)
            return self._super_map_default(super_parm)
        else:
            return res

    def _super_map_default(self, super_parm):
        return self._super_map[super_parm]['def']

    def _get_from_node_parameter(self, parm_name, super_parm_name):
        p = self._node.parm(parm_name) or self._node.parmTuple(parm_name)
        if not p:
            logger.error('Parameter not found %s.%s' % (self.op_name, parm_name))
            return self._super_map_default(super_parm_name)
        else:
            return p.eval()

    @classmethod
    def _get_super_map(cls):
        map_file = os.path.join(cls.maps_folder(), '_super_map.json')
        if not os.path.exists(map_file):
            raise Exception('Super Map not found: %s' % map_file)
        try:
            return cls.read_json(map_file)
        except Exception as e:
            raise Exception('Cant read Super Map file: %s' % str(e))

    @classmethod
    def _get_maps(cls):
        maps_folder = cls.maps_folder()
        json_maps = []
        for f in os.listdir(maps_folder):
            if f.startswith('_'):
                continue
            if os.path.splitext(f)[-1] == '.json':
                try:
                    map = cls.read_json(os.path.join(maps_folder, f))
                    json_maps.append(map)
                except:
                    logger.error('Error read map file: %s' % f)
        return json_maps

    def _load_method(self, name):
        mod_name = self._map.get('remap_module')
        if not mod_name:
            raise Exception('Remap module not defined')
        try:
            mod = imp.load_source('mod_%s' % mod_name, '%s/%s.py' % (self.maps_folder(), mod_name))
        except Exception as e:
            raise Exception('Cant import shader module %s: %s' % (mod_name, str(e)))
        if hasattr(mod, name):
            method = getattr(mod, name)
            if hasattr(method, '__call__'):
                return method
            else:
                raise Exception('Object %s.%s not callable' % (mod_name, name))
        else:
            raise Exception('Module %s have not method %s' % (mod_name, name))

    @classmethod
    def read_json(cls, path, **kwargs):
        regex = r'\s*(#|\/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-z\d\.{}]*)|((?<=\").*\"),?)(?:\s)*(((#|(\/{2})).*)|)$'
        lines = open(path).readlines()

        for index, line in enumerate(lines):
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    lines[index] = ""
                elif re.search(regex_inline, line):
                    lines[index] = re.sub(regex_inline, r'\1', line)
        return json.loads('\n'.join(lines), **kwargs)

    @staticmethod
    def maps_folder():
        return os.path.join(os.path.dirname(__file__), 'maps').replace('\\', '/')

##############

    def copy_parms_to(self, other):
        for parm_name in self._super_map.keys():
            p = other.parm(parm_name)
            if p:
                p.set(self.parm(parm_name).get())
            else:
                print 'Skip %s' % parm_name

    def to_shader(self, op_map, parent):
        """
        Create new shader from current universal map
        :param op_map: new operator map
        :param parent: parent: node
        :return: new shader
        """
        if False:
            parent = hou.node('/')
        # create node
        shader = parent.createNode(op_map['op_name'])
        # copy parameters
        for super_parm_name, shader_parm_name in op_map.get('parameters_map').items():
            new_value = self.super_map.get(super_parm_name)
            if new_value is None:
                continue
            parm = shader.parm(shader_parm_name)
            if parm:
                parm.set(new_value)
            else:
                parm = shader.parmTuple(shader_parm_name)
                if parm:
                    if isinstance(new_value, (int, float)):
                        new_value = (new_value, new_value, new_value)
                    parm.set(hou.Vector3(*new_value))
                else:
                    print 'Parameter not found: %s' % shader_parm_name
            if not parm:
                continue
            parm.set(new_value)
        # fix paths
        for parm in self._node.parmsReferencingThis():
            parm.set(shader.path())
        for parm in self._node.parent().parmsReferencingThis():
            parm.set(shader.parent().path())
        return shader

    def to_super_map(self):
        """
        Return universal map from current mode if remap exists
        :return: 
        """
        universal_map = self._get_super_map()
        super_map = {}
        for p_name, p_type, p_def in [(universal_map[i], universal_map[i + 1], universal_map[i + 2]) for i in range(0, len(universal_map), 3)]:
            # get current shader parameter name
            node_parm_name = self._map['parameters_map'].get(p_name)
            if not node_parm_name:
                continue
            # get current value
            value = None
            m = re.match(r"^:(\w+)\|\|(\w+)$", node_parm_name)
            if m:
                # it is method with default from node parm
                method, default_parm = m.groups()
                method = self._load_method(method)
                value = method(p_name)
                if value is None:
                    parm = self._node.parm(default_parm) or self._node.parmTuple(default_parm)
                    if parm:
                        value = parm.eval()
                    else:
                        raise Exception('Node %s have not parameter %s' % (self._node.path(), default_parm))
            if value is None:
                m = re.match(r"^:(\w+)$", node_parm_name)
                if m:
                    # it is method with default value from universal map defaults
                    method = m.group(1)
                    method = self._load_method(method)
                    value = method(p_name)
                    if value is None:
                        value = p_def
                    else:
                        logger.warning('Skip value %s' % p_name)
            if self._node.parm(node_parm_name):
                # it is simple read value from node
                value = self._node.parm(node_parm_name).eval()
            # save value to map
            if value is not None:
                # write to super map
                expr = self._map.get('export_value_expr', {}).get(p_name)
                if expr:
                    # eval export expression if exists
                    node = self._node
                    value = eval(expr.replace('$value', str(value)))
                super_map[p_name] = value
        return super_map
