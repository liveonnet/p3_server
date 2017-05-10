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
        assert issubclass(handler, BaseHandler)
#-#        info('process begin')
        a = time()
        hdl = handler(request)
#-#        info('handler created')
        await hdl.get_args()
#-#        info('get_args done')
        resp = await hdl
#-#        info('process done')
        if hdl.ch:
            await hdl.ch.clean()
#-#            info('commom clean done')
        if hdl.wx_mgr:
            await hdl.wx_mgr.clean()
#-#            info('wx mgr clean done')
        info('%.3fms', (time() - a) * 1000)
        return resp
    return nurse_handler

