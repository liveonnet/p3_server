#-#from inspect import isclass
from time import time
from lib.handler_lib import BaseHandler
from lib.tools_lib import pcformat
from lib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat

async def nurse_handler_factory(app, handler):
    """解析参数, 资源释放
    """
    async def nurse_handler(request):
#-#        info('process begin')
        if issubclass(handler, BaseHandler):
            a = time()
#-#            x = handler.mro()
#-#            info('%s mro\n%s', handler, '\n'.join(map(str, x)))
            hdl = handler(request)  # handler created
            await hdl.get_args()  # get_args done
            resp = await hdl  # process done
            await hdl.clean()
            info('%.3fms', (time() - a) * 1000)
            return resp
        else:
            return await handler(request)
    return nurse_handler

