from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning

async def logger_factory(app, handler):
    """只是个例子
    """
    async def logger(request):
        # 记录日志
        info('Request: %s %s' % (request.method, request.path))
        # 继续处理请求
        return await handler(request)
    return logger
