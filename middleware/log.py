from inspect import isclass
from lib.tools_lib import pcformat
from lib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat

async def logger_factory(app, handler):
    """只是个例子
    """
    async def logger(request):
        # 记录日志
        info('Request: %s %s %s', request.method, request.path, request._match_info)
#-#        info('handler: %s', handler)
#-#        info('Request headers: %s', pcformat(request.headers))
        # 继续处理请求
        if isclass(handler):  # class-based-view
            return await handler(request)
        else:
            return await handler(request)
    return logger
