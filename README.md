# Super Shader Converter

Скрипт для универсального конвертирования шейдеров между разными типами в Houdini.

### Принцип работы

Работает скрипт следующим образом:

1. Существует общая карта параметров, которые всегда встречаются в любом шейдере.
Эти параметры находятся в файле `maps/_super_map.json`. Предполагается что эти параметры в том или ном виде встречаются
в большинстве шейдеров под разными названиями (вы можете составитьс вой список таких параметров). 

2. Любой шейдер нужно пребразовать к этому списку, написав все соответствия в другом json-файле. 
Всегда можно добавлять новые параметры в `super_map` если требуется задействовать новый тип параметров.
Карта для шейдеров служит инструкцией, говорящей о том как и какие параметры считывать\записывать на ноде шейдера когда идёт обращение к параметрам супер шейдера.

3. Для преобразования одного типа шейдера в другой мы просто создаём два супер шейдера из разных нод и по списку копируем параметры с одной ноды на другую **как если бы это были одинаковые типы нод**.
 
_Пример_

```python
import hou
import super_shader
node1 = hou.node('/shop/arnoldStandart1')    
super1 = super_shader.SuperShader(node1)         # convert Arnold shader to SuperShader
node2 = hou.node('/shop/RS_Material1')    
super2 = super_shader.SuperShader(node2)         # convert RedShift shader to SuperShader

# copy diffuse color
diff = super1.parm('diffuse_color').get()
super2.parm('diffuse_color').set(diff)

# copy all parameter values
for parm_name in super1.all_super_parm_names():
    parm = super2.parm(parm_name)
    if parm:
        parm.set(super1.parm(parm_name).get())
# or shortcut
super1.copy_parms_to(super2)
```

### Создание карт

#### Super Map

Есть главная карта, описывающая все параметры супер шейдера. В любом супер шейдере нельзя прочитать параметры которых нет в этой карте.
Карта находится в файле `maps/_super_map.json`. 

> Если такого файла нет то берется файл поумолчанию `_super_map_example.json`. Для создания своей карты просто скопируйте файл `_super_map_example.json` и переименуйте в `_super_map.json`. В дальнейшем обновление скрипта не затрёт вашу карту.

В файле находится словарь, ключи которого это имя параметра. Только по этому имени можно обращаться к параметрам супер шейдера.
Значения ключей это словари с двумя полями: 

- `type` - описывает тип данных этого параметра. Используется для проверки типа, считываемого с ноды. Некоторые типы конвертируются в нужные по возможности. Например в `bool`.
  
- `default` - значение по умолчанию, используется если в какой-то карте шейдера нет описания данного параметра по разным причинам.

#### Shader Map

Для добавления нового типа шейдера нужно сделать для него карту.
Для этого создайте файл `JSON` в папке maps. Внутри нужно создать словарь, описывающий этот шейдер.
Карта содержит обязательные и не обязательные параметры. Соблюдайте соответствие типов параметров!

Для примера смотрите карту `v_fbx.json` которая работает со стандартным FBX материаом Houdini.

##### Обязательные параметры

- `name` - Используется для отображения данного шейдера в меню.

- `op_name` - Тип оператора. Используется для создания шейдера под эту карту.

- `context` - Контекст шейдера (используйте `shop` для SHOP контекста или `vop` для MAT котнекста).

- `parameters_map` - основной словарь параметров. Данный словарь в ключах содержит имя параметра супер шейдера, а в значении - имя соответствующего параметра на описываемом шейдере.

Существует несколько вариантов записи значений в `parameters_map`.

1. Просто пишем имя параметра с шейдера. В таком случае идёт обычное копирование значения с ноды шейдера в супер шейдер.

Например: 

`"diffuse_color": "Cd"`

2. Есть возможность вызвать функцию для обработки запроса. Для этого в карте должен быть объявлен параметр `remap_module`
из которого берётся эта функция. В таком случае запись будет выглядеть так:

`"diffuse_map": ":remap_parm"`

Можно создавать функции с любым именем. Эта функция будет получать всегда 3 аргумента:

- `node` - Нода шейдера с которого считываем значение

- `parm_name` - имя параметра супер шейдера которое считываем
 
- `get_value` - `True` если считываем значение с ноды через `get()` или `eval()`, и `False` если записываем через `set()`.

Если во время чтения функция возвращает `None` то это аналогично отсутствию описания данного параметра. Тогда будет использовано значение по умолчанию из `super_map`.

3. Можно использовать метод для чтения параметра с ноды но по умолчанию брать значение не из `super_map` а с параметра ноды. 
Например, я хочу вызвать функцию для поиска правильного начения параметра, но если оно не найдено то считать значение с конкретного параметра:

_используем символ `||` (или)_

`"diffuse_map": ":remap_parm||map1"`

В этом случае будет вызван метод `remap_parm`, но если он вернёт `None` то сначала мы попробуем считать значение параметра `Cd`, и если такового не найдется, тогда берём значение по умолчанию из `super_map`.
Поддерживается только один параметр. То есть нельзя написать так `"diffuse_map": ":remap_parm||map1||map2||map3"`. Такая запись игнорируется!

4. Если в значение написать `null`, то это аналогично отсутствию данного параметра на ноде. 
Например данный шейдер не поддерживает такое свойство. В этом случае можно строку вообще не писать. Значение будет браться из `super_map`.

##### Необязательные параметры

- `remap_module` - нужен если у вас есть вызов функции для чтения параметра. Модуль должен находиться в папке `maps`. Внутри модуля можно создавать любые функции и прописывать их в карте в формате:

`:{func_name}`

Например:

`:get_vray_parameter`

Эти функции нужны для непрямого преобразования параметра. Когда простого копиования не достаточно и нужны манипуляции с нодами.

- `allow_creation` - позволяет добавить этот шейдер в меню для создания новых шейдеров. Если false то из такого шейдера можно считать информацию но создать новый не получится. По умолчанию false.

- `set_value_expr` и `get_value_expr` - экспрешены для быстрого преобразования значений. Это словари в ключах которых находится имя супер параметра а в значении экспрешен в виде строки.

В самом экспрешене используйте переменную `$value` для подстановки оригинального значения.

Например, предположим что в супер шейдере есть параметр `specular_roughness` который находится в диапазоне 0-1. Но в нашем шейдере этот диапазон равен 0-100 и означает обратный эффект (не размытость а глянцевость). Задача супершейдера содержать одинаковые, унифицированные значения и преобразовывать их в подходящие для любого шейдера.
Тогда нам потребуются такие преобразования:

```json
{
 "set_value_expr":{
    "":"complement and multiply by 100",
    "specular_roughness": "int((1-$value)*100)" 
  },
  "get_value_expr": {
    "":"divide by 100, complement and round",
    "specular_roughness": "round(1-($value*0.01), 3)"
  }
}
```

> Проще всего скопировать готовую карту и заменить параметры. 
> Главное — не пропустить ни одного параметра и правильно написать строгое соответствие параметров.
    

### Готовые функции

В модуле `shader_converter` есть готовые функции.

- `convert` - преобразует выделеные ноды в новый тип шейдера. Будет создана новая нода и скопированы все параметры. Для выбора типа откроется меню.

- `convert_and_replace` - аналогична функции `convert`, но после создания нового шейдера все ссылки на на старый шейдер будут заменены ссылками на новый шейдер.

- `open_new_shader_menu` - открывает меню со списокм всех доступных карт шейдеров для выбора нового типа шейдера во время конверирования. Используется в функции `convert`.

### Shelf Button

Готовый код для быстрого преобразования выделенных нод

```python
import super_shader

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
```

Данный код поместите в кнопку на полку. После нажатия на кнопку появится меню с выбором типа в который нужно преобразовать выделенные ноды.


### ToDo

Идеи для реализации.

- Копирование коннектов

- Добавление любых типов шейдерных нод для преобразования всего нетворка

- Сохранение шейдера в JSON пресет `super_map` и создание шейдера из этого пресета (для аавто переноса переноса между софтами используя meta_data)

- Вынести весь Houdini-зависимый функционал отдельно чтобы ядро можно было использовать в разных софтах.
