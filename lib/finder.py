from re import compile
from .namespace import Namespace
from .place import Place
from .middleware import Middleware
from .console import Console
from .router import Router
from .language import Language
from .blade import Blade
from .attribute import Attribute
from .config import Config
from .inertia import Inertia
from .livewire import Livewire
from .classname import ClassName
from .setting import Setting


def get_place(selection):
    line = selection.get_line()
    lines = selection.get_lines_after_delimiter()

    path = selection.get_path()

    places = (
        path_helper_place,
        static_file_place,
        env_place,
        config_place,
        filesystem_place,
        lang_place,
        inertia_place,
        livewire_place,
        component_place,
        middleware_place,
        command_place,
        route_place,
        attribute_place,
        blade_place,
        controller_place,
        class_name_place,
    )

    for fn in places:
        place = fn(path, line, lines, selection)
        if place:
            place.source = fn.__name__
            return place


def set_controller_action(path, action, blocks):
    ''' set the controller action '''

    path = path.replace('@', '.php@')
    path = path.replace('::class', '.php')
    if action:
        path = path + '@' + action

    elif len(blocks) and blocks[0]['is_namespace'] is False:
        """resource or controller route"""
        new_path = blocks[0]['namespace']
        if new_path != path:
            path = new_path + '.php@' + path
        else:
            path = new_path + '.php'

    return path


def set_controller_namespace(path, selected, ns):
    ''' set the controller namespace '''

    if '\\' != path[0] and ns:
        # it's not absolute path namespace, get group namespace
        path = ns + '\\' + path.lstrip('\\')

    return path


def controller_place(path, line, lines, selected):
    namespace = Namespace(selected.view)
    blocks = namespace.get_blocks(selected)
    is_controller = "Controller" in lines or selected.is_class

    if is_controller is False and 0 == len(blocks):
        return False

    action = None
    pattern = compile(r"""\[\s*(.*::class)\s*,\s*["']([^"']+)""")
    matched = pattern.search(line) or pattern.search(lines)
    if (matched and path == matched.group(2)):
        path = matched.group(1)
        action = matched.group(2)

    path = set_controller_action(path, action, blocks)

    ns = namespace.find(blocks)
    path = set_controller_namespace(path, selected, ns)

    place = Place(path)
    place.is_controller = True
    return place


def config_place(path, line, lines, selected):
    config = Config()
    place = config.get_place(path, line, lines)
    return place


def filesystem_place(path, line, lines, selected):
    pattern = compile(r"""Storage::disk\(\s*['"]([^'"]+)""")
    matched = pattern.search(line) or pattern.search(lines)
    if (matched and path == matched.group(1)):
        path = 'config/filesystems.php'
        location = "(['\"]{1})" + matched.group(1) + "\\1\\s*=>"
        return Place(path, location)

    return False


def inertia_place(path, line, lines, selected):
    inertia = Inertia()
    place = inertia.get_place(path, line, lines)
    return place


def livewire_place(path, line, lines, selected):
    livewire = Livewire()
    place = livewire.get_place(path, line, lines)
    return place


def lang_place(path, line, lines, selected):
    lang_patterns = [
        compile(r"""__\([^'"]*(['"])([^'"]*)\1"""),
        compile(r"""@lang\([^'"]*(['"])([^'"]*)\1"""),
        compile(r"""trans\([^'"]*(['"])([^'"]*)\1"""),
        compile(r"""trans_choice\([^'"]*(['"])([^'"]*)\1"""),
    ]

    language = None
    for pattern in lang_patterns:
        matched = pattern.search(line) or pattern.search(lines)
        if (not matched or path != matched.group(2)):
            continue

        if not language:
            language = Language()
        place = language.get_place(path)
        return place

    return False


def static_file_place(path, line, lines, selected):
    find = (path.split('.')[-1].lower() in Setting().exts())
    if find is False:
        return False

    # remove dot symbols
    split = list(filter(
        lambda x: x != '..' and x != '.',
        path.split('/')))
    return Place('/'.join(split))


def env_place(path, line, lines, selected):
    env_pattern = compile(r"""env\(\s*(['"])([^'"]*)\1""")
    matched = env_pattern.search(line) or env_pattern.search(lines)
    find = (matched and path == matched.group(2))
    if find:
        return Place('.env', path)
    return False


def component_place(path, line, lines, selected):
    component_pattern = compile(r"""<\/?x-([^\/\s>]*)""")
    matched = component_pattern.search(line) or component_pattern.search(lines)
    if matched is None:
        return False

    path = matched.group(1).strip()

    split = path.split(':')
    vendor = 'View/Components/'
    res_vendor = 'views/components/'
    # vendor or namespace
    if (3 == len(split)):
        # vendor probably is lowercase
        if (split[0] == split[0].lower()):
            vendor = split[0] + '/'
            res_vendor = split[0] + '/'

    sections = split[-1].split('.')
    place = Place(res_vendor + '/'.join(sections) + '.blade.php')
    place.paths.append(place.path)

    for i, s in enumerate(sections):
        sections[i] = s.capitalize()
    sections[-1] = camel_case(sections[-1])
    place.paths.append(vendor + '/'.join(sections) + '.php')

    return place


def camel_case(snake_str):
    components = snake_str.split('-')
    return components[0].title() + ''.join(x.title() for x in components[1:])


def attribute_place(path, line, lines, selected):
    attribute = Attribute()
    place = attribute.get_place(path, line, lines)
    return place


def blade_place(path, line, lines, selected):
    blade = Blade()
    place = blade.get_place(path, line, lines)
    return place


def path_helper_place(path, line, lines, selected):
    path_helper_pattern = compile(r"""([\w^_]+)_path\(\s*(['"])([^'"]*)\2""")
    matched = path_helper_pattern.search(line) or\
        path_helper_pattern.search(lines)
    if (matched and path == matched.group(3)):
        prefix = matched.group(1) + '/'
        if 'base/' == prefix:
            prefix = ''
        elif 'resource/' == prefix:
            prefix = 'resources/'

        return Place(prefix + path)
    return False


def middleware_place(path, line, lines, selected):
    middleware_patterns = [
        compile(r"""[m|M]iddleware\(\s*\[?\s*(['"][^'"]+['"]\s*,?\s*)+"""),
        compile(r"""['"]middleware['"]\s*=>\s*\s*\[?\s*(['"][^'"]+['"]\s*,?\s*){1,}\]?"""),
    ]
    middlewares = None
    for pattern in middleware_patterns:
        matched = pattern.search(line) or pattern.search(lines)
        if not matched:
            continue

        if not middlewares:
            middleware = Middleware()
            middlewares = middleware.all()

        # remove middleware parameters
        alias = path.split(':')[0]
        place = middlewares.get(alias)
        if place:
            return place


def command_place(path, line, lines, selected):
    patterns = [
        compile(r"""Artisan::call\(\s*['"]([^\s'"]+)"""),
        compile(r"""command\(\s*['"]([^\s'"]+)"""),
    ]

    commands = None
    for pattern in patterns:
        match = pattern.search(line) or pattern.search(lines)
        if not match:
            continue

        if not commands:
            console = Console()
            commands = console.all()

        signature = match.group(1)
        place = commands.get(signature)
        if place:
            return place

        return place


def route_place(path, line, lines, selected):
    patterns = [
        compile(r"""route\(\s*['"]([^'"]+)"""),
        compile(r"""['"]route['"]\s*=>\s*(['"])([^'"]+)"""),
    ]

    routes = None
    for pattern in patterns:
        match = pattern.search(line) or pattern.search(lines)
        if not match:
            continue

        if not routes:
            router = Router()
            routes = router.all()

        place = routes.get(match.group(1))
        if place:
            return place

        return place


def class_name_place(path, line, lines, selected):
    class_name = ClassName()
    place = class_name.get_place(path, line, lines)
    return place
