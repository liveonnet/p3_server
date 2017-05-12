#-#from aiohttp import web
#-#from asyncio import CancelledError
#-#from random import randrange
#-#from random import choice
from aiohttp import web
#-#from asyncio import sleep
from lib.wx_lib import WXManager
from lib.tools_lib import pcformat
from lib.tools_lib import check_wx_auth
from lib.conf_lib import conf
from lib.tools_lib import get_wx_auth
from lib.handler_lib import BaseHandler
from lib.handler_lib import route
#-#from lib.cache_lib import K
from lib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


@route('/wx_auth')
class WxHandler(BaseHandler):
    def __init__(self, req):
        super().__init__(req)
        self.wx_mgr = WXManager(conf['loop'], self)

    async def clean(self):
        await super().clean()
        await self.wx_mgr.clean()
#-#        info('wx_mgr clean done')

    async def get(self):
        (sig, timestamp, nonce, echostr), l_err = self.get_my_arg('signature', 'timestamp', 'nonce', 'echostr')
        token = conf['wx_token']
        if check_wx_auth(token, timestamp, nonce, sig):
            info('auth ok!')
            return web.Response(text=echostr)
        else:
            info('my sig %s', get_wx_auth(token, timestamp, nonce))
        return web.Response(text='auth failed!')

    async def post(self):
        (nonce, encrypt_type, msg_sign, timestamp), l_err = self.get_my_arg('nonce required&bytes', 'encrypt_type required&bytes', 'msg_signature required&bytes', 'timestamp required&bytes')
        d = self.wx_mgr.extractXml(nonce, encrypt_type, msg_sign, timestamp, await self.request.text())
#-#        info('decrypted msg:\n%s', pcformat(d))
        message_type = d['MsgType']  # text/event
        ret_type, ret_data = await getattr(self, 'on_%s' % message_type, self.on_dft)(timestamp, nonce, encrypt_type, msg_sign, d)

        if ret_type == 'text':
            resp = self.wx_mgr.createText(nonce, encrypt_type, d['FromUserName'], d['ToUserName'], ret_data)
        elif ret_type == 'image':
            resp = self.wx_mgr.createImage(nonce, encrypt_type, d['FromUserName'], d['ToUserName'], ret_data)
        elif ret_type == 'raw':
            resp = ret_data
        else:
            info('unknown ret_type %s, will send to client derectly !!!', ret_type)

        info('[%s]%s << %s', ret_type, d['ToUserName'], ret_data)
#-#        info('resp: %s', resp)
        return web.Response(headers={'Content-Type': 'application/xml'}, text=resp)

    async def on_dft(self, timestamp, nonce, encrypt_type, msg_sign, in_data):
        u'''默认消息处理函数
        '''
        ret_type, ret_data = 'text', u'收到~'
        info('不支持的消息类型 %s\n%s', in_data['MsgType'], pcformat(in_data))
        return ret_type, ret_data

    async def on_text(self, timestamp, nonce, encrypt_type, msg_sign, in_data):
        u'''接收文本消息
        '''
        info('[%s]%s >> %s', in_data['MsgType'], in_data['FromUserName'], in_data['Content'])
        ret_type = 'text'
        ret_data = await self.getAutoReply(timestamp, nonce, encrypt_type, msg_sign, in_data)
        if ret_data:
            info('自动回复[:20] %s', ret_data[:20])
#-#        elif in_data['FromUserName'] == 'owD3VszZ1r115U-DVYLMdCWU1AVE':
#-#            pass
        else:
            ret_data = (in_data['Content'] + ', ' if in_data['Content'] else '') + 'yeah, got it~'
        return ret_type, ret_data

    async def getAutoReply(self, timestamp, nonce, encrypt_type, msg_sign, in_data):
            u'''获取自动回复匹配
            '''
            s1 = u'''感谢关注《XXXX》，商务合作请洽关小姐，联系方式：XXXX@dianjoy.com 。'''
            s2 = u'''(づ￣ 3￣)づ'''
            s3 = u'''亲如果有问题要问，请留言给客服qq：xxxxxxx

    注意：找“生活服务”而不是“人”喔~

    不需要加好友就可以直接留言喔~~~

    客服美眉会在工作时间（周一到周五10：00~19:00）逐一回复~~(づ￣ 3￣)づ'''
            s4 = u'''您好~非常感谢您对《XXXX》的关注！您的这种情况可能是因为网络问题造成的。


     亲如果还有其他问题，请留言给客服qq：xxxx


    注意：找“生活服务”而不是“人”喔~

    不需要加好友就可以直接留言喔~~~

    客服美眉会在工作时间（周一到周五10：00~19:00）逐一回复~~(づ￣ 3￣)づ'''

            d_auto = {(u'商务合作', ): s1,
                      (u'dd', u'红包', u'活动'): s2,
                      (u'你好', u'问题', u'客服', u'人工客服', u'人工', u'客服qq', u'有人吗', u'在吗'): s3,
                      (u'不给我钱', u'不给钱', u'没有广告', u'没有任务', u'任务做完了', u'任务没了'): s4,
                      }

            reply = ''
            content = in_data['Content']
            if not in_data['Content']:
                return ''
            for _l_k, _v in d_auto.items():
                for _k in _l_k:
                    if _k in content:
                        reply = _v
                        break
            return reply

    async def on_subscribe(self, timestamp, nonce, encrypt_type, msg_sign, in_data):
        u'''关注
        '''
        ret_type = 'text'
        ret_data = u'''你终于来了~ (●'◡'●) 点击菜单↓↓↓参加最新活动~'''
        event_key = in_data['EventKey']
        openid = in_data['FromUserName']
        wx_user = await self.wx_mgr.getUserInfo(openid)
        unionid = wx_user.get('unionid', '')
        info('unionid %s', unionid)
#-#        db = self.db()
#-#        uid = User.createUser(db, wx_user)
        scene_id = None

        if event_key and event_key.startswith('qrscene_'):
            ticket = in_data['Ticket']
            scene_id = event_key[8:]
            info('%s 通过扫二维码关注 scene_id %s ticket %s', openid, scene_id, ticket)
#-#            WxEventHistory.logEvent(db, openid, unionid, 2)
        else:
            info('%s 关注', in_data['FromUserName'])
#-#            WxEventHistory.logEvent(db, openid, unionid, 1)

#-#        # 对扫码关注，需要查找scene_id是否是处于砍价状态的订单
#-#        if scene_id:
#-#            # 调用砍价接口
#-#            r = Order.bargain(scene_id, uid)
#-#            if r['code'] == 1:  # 砍价成功
#-#                # TODO 给A发模板消息
#-#                # TODO 模板消息url点击后可以直接以登陆状态跳到特定砍价订单页面
#-#                # 先用客服消息简化代替
#-#                order_user_info = User.getUserInfoByOrderId(db, scene_id)
#-#                msg = '您的好友%s帮您把订单%s的价格砍到了%s, 砍掉了%s' % (wx_user['nickname'], scene_id, r['price'], r['money'])
#-#                info('send msg: %s', msg)
#-#                r = yield WXManager.kfSendTextMsg(order_user_info.openid, msg)
#-#                # TODO 给B发文本回复
#-#                msg = '您帮uid为%s的用户将订单%s砍到了%s, 砍掉了%s' % (uid, scene_id, r['price'], r['money'])
#-#                info('send msg: %s', msg)
#-#                r = yield WXManager.kfSendTextMsg(wx_user['openid'], msg)
#-#            else:  # TODO 砍价不成功
#-#                info('砍价没成功？ %s %s', r['code'], r['info'])
        return ret_type, ret_data

    async def on_unsubscribe(self, timestamp, nonce, encrypt_type, msg_sign, in_data):
        """取消关注
        """
        ret_type, ret_data = 'text', 'success'
        info('%s 取消了关注', in_data['FromUserName'])

        openid = in_data['FromUserName']
        wx_user = await self.wx_mgr.getUserInfo(openid)
        openid = in_data['FromUserName']  # TODO
        unionid = wx_user.get('unionid', '')
        info('unionid %s', unionid)
#-#        db = self.db()
#-#        User.updateUserWxStatus(db, openid, 0)
#-#        WxEventHistory.logEvent(db, openid, unionid, 0)

        return ret_type, ret_data

