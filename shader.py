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
        """
        Get super parm by name
        :param node_parm_name: super name 
        :return: Parm
        """
        if node_parm_name in self._map['parameters_map']:
            return self.Parm(node_parm_name, self.__get_parm_value, self.__set_parm_value)

    def __get_parm_value(self, super_name):
        """
        Get value callback
        :param super_name: super name 
        :return: value
        """
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
        """
        Set value callback
        :param super_name: super name 
        :param value: new value
        :return: True or False
        """
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
        """
        Set value to original node
        :param parm_name: node parm name
        :param value: new value
        :param super_name: super name
        :return: success bool
        """
        p = self._node.parm(parm_name)
        value_type = self._super_map.get(super_name).get('type')
        value = self._apply_expression(value, super_name)
        value = self.convert_type(value, value_type)
        if p:
            p.set(self._apply_expression(value, super_name))
            return True
        else:
            p = self._node.parmTuple(parm_name)
            if p:
                # value should be list or tuple
                p.set(hou.Vector3(*value))
                return True
        return False

    def convert_type(self, value, type):
        if type == 'vec':
            if not isinstance(value, (list, tuple)) or not len(value) == 3:
                raise Exception('Wrong value for type %s: %s' % (type, value))
            return list(value)
        elif type == 'flt':
            try:
                return float(value)
            except:
                raise Exception('Wrong value for type %s: %s' % (type, value))
        elif type == 'int':
            try:
                return int(value)
            except:
                raise Exception('Wrong value for type %s: %s' % (type, value))
        elif type == 'bol':
            try:
                return bool(value)
            except:
                raise Exception('Wrong value for type %s: %s' % (type, value))
        elif type == 'str':
            if isinstance(value, (str, unicode)):
                return str(value)
            else:
                raise Exception('Wrong value for type %s: %s' % (type, value))


    def _apply_expression(self, value, super_parm_name, set_value=True):
        """
        Apply parameter expression
        :param value: value
        :param super_parm_name: super name 
        :param set_value: set value or get value mode
        :return: new value
        """
        expr = self._map.get('set_value_expr' if set_value else 'get_value_expr', {}).get(super_parm_name)
        if expr:
            if isinstance(value, (str, unicode)):
                value = '"%s"' % value
            else:
                value = str(value)
            value = eval(expr.replace('$value', value))
        return value

    def _get_from_method_or_default(self, method, super_parm, default_parm=None, get_value=True):
        """
        Execute method
        :param method: method name 
        :param super_parm: super name
        :param default_parm: default node parm name
        :param get_value: get value or set value (bool)
        :return: 
        """
        m = self._load_method(method)
        res = m(self._node, super_parm, get_value)
        if res is None:
            if default_parm:
                return self._get_from_node_parameter(default_parm, super_parm)
            return self._super_map_default(super_parm)
        else:
            return res

    def _super_map_default(self, super_parm):
        """
        Return default value from super map
        :param super_parm: super name
        :return: 
        """
        return self._super_map[super_parm]['default']

    def _get_from_node_parameter(self, parm_name, super_parm_name):
        """
        Return value from node
        :param parm_name: node parm name
        :param super_parm_name: super name (for default value)
        :return: 
        """
        p = self._node.parm(parm_name) or self._node.parmTuple(parm_name)
        if not p:
            logger.error('Parameter not found %s.%s' % (self.op_name, parm_name))
            return self._super_map_default(super_parm_name)
        else:
            return p.eval()

    @classmethod
    def _get_super_map(cls):
        """
        Return super map
        :return: dict
        """
        map_file = os.path.join(cls.maps_folder(), '_super_map.json')
        if not os.path.exists(map_file):
            map_file = os.path.join(cls.maps_folder(), '_super_map_example.json')
            if not os.path.exists(map_file):
                raise Exception('Super Map not found: %s' % map_file)
        try:
            return cls.read_json(map_file)
        except Exception as e:
            raise Exception('Cant read Super Map file: %s' % str(e))

    @classmethod
    def _get_maps(cls):
        """
        Return list of all existing maps
        :return: [{},...]
        """
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
                    print 'Error read map file: %s' % f
                    logger.error('Error read map file: %s' % f)
        return json_maps

    def _load_method(self, name):
        """
        Load module by name
        :param name: module name
        :return: object
        """
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
        """
        Read commented JSON
        :param path: file path
        :param kwargs: 
        :return: object
        """
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
        """
        Return path to maps folder
        :return: str 
        """
        return os.path.join(os.path.dirname(__file__), 'maps').replace('\\', '/')

    def all_super_parm_names(self):
        """
        Return all parameter names from super map
        :return: list
        """
        return self._super_map.keys()

    def copy_parms_to(self, other):
        """
        Copy parameters from current super shader to other
        :param other: SuperShader
        :return: 
        """
        if not isinstance(other, SuperShader):
            raise Exception('You should pass SuperShader instance only')
        for parm_name in self.all_super_parm_names():
            p = other.parm(parm_name)
            if p:
                src = self.parm(parm_name)
                if src:
                    value = src.get()
                else:
                    value = self._super_map_default(parm_name)
                p.set(value)
