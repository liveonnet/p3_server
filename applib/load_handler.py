import os
import inspect
import importlib
from applib.handler_lib import BaseHandler
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning


def is_package(path):
    """判断一个路径是否是一个包
    """
    return os.path.isdir(path) and os.path.exists(os.path.join(path, '__init__.py'))


def setup_routes(app):
    """从model目录导入基于BaseHandler的处理类，加入路由
    """
    base_path = os.path.abspath(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             os.path.pardir),
                                'model'))
    debug('import base_path %s', base_path)
    for _dirpath, _dirnames, _filenames in os.walk(base_path):
        l_ignore_dir = filter(lambda x: x.startswith('.'), _dirnames)
        for _dir in l_ignore_dir:
            info('remove %s', _dir)
            _dirnames.remove(_dir)

        if is_package(_dirpath) and _filenames:
            # 得到包名
            pkg_name = _dirpath[len(base_path) + len(os.sep):].replace('/', '.') or 'model'
            _filenames = filter(lambda x: x.endswith('_handler.py'), _filenames)
            #得到handler结尾的py文件列表，依次作为模块导入
            for _file in _filenames:
                try:
                    mod = importlib.import_module('%s.%s' % (pkg_name, os.path.splitext(_file)[0]), pkg_name)
                except Exception as e:
                    warn('import error %s %s', '%s.%s' % (pkg_name, os.path.splitext(_file)[0]), e)
                else:
                    # 导入模块中的处理类
                    # 模块中可导入的处理类必须满足如下条件:
                    # 不以_开头 and 必须是类 and 不是BaseHandler and 是BaseHandler的子类
                    for _class in (x for x in map(lambda x: getattr(mod, x),
                                                  filter(lambda x: not x.startswith('_'), dir(mod))) if inspect.isclass(x) and x is not BaseHandler and issubclass(x, BaseHandler)):
                        info('add_router %s %s', repr(_class.PATH), _class)
                        app.router.add_route('*', _class.PATH, _class().handle)
