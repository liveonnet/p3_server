#coding=utf8

import os
import logging
import logging.handlers
import socket
#-#from multiprocessing import Queue
#-#import threading
#-#import traceback
#-#from urllib.parse import unquote
#-#from io import StringIO
#-#import types
#-#from Queue import Empty
#-#from time import sleep
#-#from cPickle import dumps
#-#from cPickle import loads
import sys
import struct
from logging import Formatter
#-#import tornado.log
#-#from tornado.log import LogFormatter
#-#from tornado.options import options as _options
#-#from lib.redis_manager import m_redis
#-#from redis import ConnectionError
#-#from lib.jsonlogger import JsonFormatter

#-## for sphinx autodoc
#-## to show original function's signature instead of decorator's
#-## http://stackoverflow.com/questions/3687046/python-sphinx-autodoc-and-decorated-members
#-#try:
#-#    from decorator import decorator
#-#except ImportError:
#-#    pass
#-#else:
#-#    from tornado import gen
#-#    gen.coroutine = decorator(gen.coroutine)

if os.name != 'nt':
    import fcntl


def get_lan_ip():
    interfaces = [
        'eth0',
        'eth1',
        'eth2',
        'wlan0',
        'wlan1',
        'wifi0',
        'ath0',
        'ath1',
        'ppp0',
    ]
    ip = socket.gethostbyname(socket.gethostname())
    if os.name != 'nt':
        for ifname in interfaces:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname.encode('utf8'))))[20:24])
                break
            except IOError:
                pass
    return ip


class MPFormatter(logging.Formatter):
    u'''定制多进程文件日志输出格式
    '''
    server = get_lan_ip()

    def format(self, record):
        record.server = self.__class__.server
        return super(MPFormatter, self).format(record)


class MyDatagramHandler(logging.handlers.DatagramHandler):
    u'''定制DatagramHandler
    与DatagramHandler的区别：
    1 不传原始record而传format后的字符串
    2 过滤部分日志
    '''
    ip = get_lan_ip()

    def emit(self, record):
        try:
            s = self.makePickle(record)
            if s:
                self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def makePickle(self, record):
        record.ip = self.__class__.ip
        try:
            if record.args:
                record.msg = record.msg % record.args
                record.args = None

#-#            if record.exc_info:
#-#                if not isinstance(self.formatter, JsonFormatter):
#-#                    self.format(record)
#-#                    record.exc_info = None

            if not isinstance(record.msg, dict):
                if record.msg.startswith(('200 ', '304 ', '302 ')) and not record.exc_info:  # 没有异常的情况下，日志文件里不记录成功的访问请求
                    return
            else:
                if record.msg.get('code', None) in (200, 304, 302) and not record.exc_info:  # 没有异常的情况下，日志文件里不记录成功的访问请求
                    return
            return self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class ErrorFilter(logging.Filter):
    u'''忽略除 INFO/DEBUG 以外的日志
    '''
    def filter(self, record):
        return record.levelname not in ('INFO', 'DEBUG')


class DebugFilter(logging.Filter):
    u'''只处理 INFO/DEBUG 类型日志
    '''
    def filter(self, record):
        return record.levelname in ('INFO', 'DEBUG')


class InternalLog(object):
    u'''日志类，实现file和console分开输出
    '''
    _logger = None

    @classmethod
    def getLogger(cls):
        if cls._logger:
            print('use existing logger')
            return cls._logger

        logging.captureWarnings(True)
        cls._logger = logging.getLogger()
        cls._logger.setLevel(logging.DEBUG)
        cls._logger.propagate = 0
        # remove existing handler from root logger
        l_2del = [_h for _h in cls._logger.handlers if isinstance(_h, logging.StreamHandler)]
        for _h in l_2del:
            cls._logger.removeHandler(_h)

        # stream log
        log_sh = logging.StreamHandler(sys.stdout)
        log_sh.setLevel(logging.INFO)
        fmt = Formatter('%(asctime)s %(levelname)s %(processName)s %(module)s %(funcName)s %(lineno)d | %(message)s', '%H:%M:%S')
        log_sh.setFormatter(fmt)
        print('logger handler StreamHandler init done.')

        log_handlers = [log_sh]
        for hdl in log_handlers:
            cls._logger.addHandler(hdl)  # add handler(s) to root logger
            if isinstance(hdl, logging.handlers.RotatingFileHandler) or isinstance(hdl, logging.FileHandler):
                print('log file %s %s' % (hdl.baseFilename, hdl.mode))
        cls._logger.info('root logger init done. script dir %s' % (os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)), ))
        return cls._logger


app_log = InternalLog.getLogger()
info, debug, error = app_log.info, app_log.debug, app_log.error

#-#if __file__[-4:].lower() in ['.pyc', '.pyo']:
#-#    _srcfile = __file__[:-4] + '.py'
#-#else:
#-#    _srcfile = __file__
#-#_srcfile = os.path.normcase(_srcfile)
#-#
#-#
#-#def tmp_findCaller(self):
#-#    """
#-#    Find the stack frame of the caller so that we can note the source
#-#    file name, line number and function name.
#-#    """
#-#    f = sys._getframe(2)
#-#    #On some versions of IronPython, currentframe() returns None if
#-#    #IronPython isn't run with -X:Frames.
#-#    if f is not None:
#-#        f = f.f_back
#-#    rv = "(unknown file)", 0, "(unknown function)"
#-#    while hasattr(f, "f_code"):
#-#        co = f.f_code
#-#        filename = os.path.normcase(co.co_filename)
#-#        if filename == _srcfile:
#-#            f = f.f_back
#-#            continue
#-#        rv = (co.co_filename, f.f_lineno, co.co_name)
#-#        break
#-#    return rv
#-#
#-#
#-#def mod_findCaller(self):
#-#    """
#-#    Find the stack frame of the caller so that we can note the source
#-#    file name, line number and function name.
#-#    """
#-#    f = sys._getframe(2)
#-#    #On some versions of IronPython, currentframe() returns None if
#-#    #IronPython isn't run with -X:Frames.
#-#    if f is not None:
#-#        f = f.f_back
#-#    rv = "(unknown file)", 0, "(unknown function)"
#-#    while hasattr(f, "f_code"):
#-#        co = f.f_code
#-#        filename = os.path.normcase(co.co_filename)
#-#        if filename == _srcfile:
#-#            f = f.f_back
#-#            continue
#-#        rv = (co.co_filename, f.f_lineno, co.co_name)
#-#        break
#-#    return rv
#-#
#-#
#-#def info(self, msg, *args, **kwargs):
#-#    ei = kwargs.get('exc_info')
#-#    if ei:
#-#        if not isinstance(ei, tuple):
#-#            ei = sys.exc_info()
#-#        if ei[0]:
#-#            sio = StringIO()
#-#            traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
#-#            s = sio.getvalue()
#-#            sio.close()
#-#            if s[-1:] == "\n":
#-#                s = s[:-1]
#-#            outer_frame = sys._getframe(1)
#-#            if outer_frame:
#-#                obj = outer_frame.f_locals.get('self') or outer_frame.f_locals.get('handler')
#-#                if obj:
#-#                    md = sys.modules.get('lib.formwork')
#-#                    if md:
#-#                        hdl_class = getattr(md, 'SuperRequestHandler')
#-#                        if hdl_class and isinstance(obj, hdl_class):
#-#                            co = outer_frame.f_code
#-#                            j_data = {'message': msg % args, 'method': obj.request.method, 'api': obj.request.uri[1:obj.request.uri.find('.do')], 'url': unquote(obj.request.uri), 'remote': obj.request.remote_ip, 'exc': s, 'funcName': co.co_name, 'lineno': outer_frame.f_lineno, 'filename': co.co_filename, 'class': str(obj)}
#-#                            old_func = self.findCaller
#-#                            self.findCaller = types.MethodType(tmp_findCaller, self)
#-#                            self.real_info(j_data)
#-#                            self.findCaller = old_func
#-#                            return
#-#    return self.real_info(msg, *args, **kwargs)
#-#
#-#
#-#def error(self, msg, *args, **kwargs):
#-#    ei = kwargs.get('exc_info')
#-#    if ei:
#-#        if not isinstance(ei, tuple):
#-#            ei = sys.exc_info()
#-#        if ei[0]:
#-#            sio = StringIO()
#-#            traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
#-#            s = sio.getvalue()
#-#            sio.close()
#-#            if s[-1:] == "\n":
#-#                s = s[:-1]
#-#            outer_frame = sys._getframe(1)
#-#            if outer_frame:
#-#                obj = outer_frame.f_locals.get('self') or outer_frame.f_locals.get('handler')
#-#                if obj:
#-#                    md = sys.modules.get('lib.formwork')
#-#                    if md:
#-#                        hdl_class = getattr(md, 'SuperRequestHandler')
#-#                        if hdl_class and isinstance(obj, hdl_class):
#-#                            co = outer_frame.f_code
#-#                            j_data = {'message': msg % args, 'method': obj.request.method, 'api': obj.request.uri[1:obj.request.uri.find('.do')], 'url': unquote(obj.request.uri), 'remote': obj.request.remote_ip, 'exc': s, 'funcName': co.co_name, 'lineno': outer_frame.f_lineno, 'filename': co.co_filename, 'class': obj.__class__.__name__}
#-#                            old_func = self.findCaller
#-#                            self.findCaller = types.MethodType(tmp_findCaller, self)
#-#                            self.real_error(j_data)
#-#                            self.findCaller = old_func
#-#                            return
#-#    return self.real_error(msg, *args, **kwargs)
#-#
#-#
#-#def debug(self, msg, *args, **kwargs):
#-#    return self.real_debug(msg, *args, **kwargs)
#-#
#-#
#-#def warning(self, msg, *args, **kwargs):
#-#    return self.real_warning(msg, *args, **kwargs)
#-#
#-#
#-#app_log.real_info = app_log.info
#-#app_log.real_error = app_log.error
#-#app_log.real_debug = app_log.debug
#-#app_log.real_warning = app_log.warning
#-#
#-#app_log.info = types.MethodType(info, app_log)
#-#app_log.error = types.MethodType(error, app_log)
#-#app_log.debug = types.MethodType(debug, app_log)
#-#app_log.warning = types.MethodType(warning, app_log)
#-#app_log.findCaller = types.MethodType(mod_findCaller, app_log)


#-#def mylog_func(handler):
#-#    u'''给tornado内部用的日志函数
#-#    '''
#-#    use_json = False  # 出错时输出json格式数据，其他情况下输出str
#-#    if handler.get_status() < 400:
#-##-#        return # 这里return可以在文件和console中都不输出成功的访问日志
#-#        log_method = app_log.real_info
#-#    elif handler.get_status() < 500:
#-#        log_method = app_log.real_warning
#-#    else:
#-#        log_method = app_log.real_error
#-#        use_json = True
#-#
#-#    request_time = 1000.0 * handler.request.request_time()
#-#    if not use_json:
#-#        log_method('%d %s %.2fms', handler.get_status(), unquote(handler._request_summary()), request_time)
#-#    else:
#-#        j_data = {'code': handler.get_status(), 'method': handler.request.method, 'api': handler.request.uri[1:handler.request.uri.find('.do')], 'url': unquote(handler.request.uri), 'remote': handler.request.remote_ip, 'req_time': '%.2f' % request_time}
#-#        if getattr(handler, 'exc_data', None) and handler.exc_data:
#-#            j_data['exc'] = handler.exc_data
#-#        log_method(j_data)
#-#
