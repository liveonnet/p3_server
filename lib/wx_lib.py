# -*- coding: utf-8  -*-
import time
import json
import random
import string
import asyncio
import aiohttp
from aiohttp.resolver import AsyncResolver
from hashlib import md5
from urllib.parse import quote
#-#from operator import itemgetter
#-#from itertools import chain
#-#from cStringIO import StringIO
if __name__ == '__main__':
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from lib.conf_lib import conf
from lib.WXBizMsgCrypt import WXBizMsgCrypt
from lib.tools_lib import pcformat
from lib.tools_lib import parseXml2Dict
from lib.applog import app_log
info, debug, error = app_log.info, app_log.debug, app_log.error


class WXManager(object):
    """微信公众号功能管理类
    """

    # 文本消息模板
    TPL_RETURN_TEXT = '''<xml>
<ToUserName><![CDATA[{TOUSER}]]></ToUserName>
<FromUserName><![CDATA[{FROMUSER}]]></FromUserName>
<CreateTime>{TIME}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{CONTENT}]]></Content>
</xml>'''
    # 图片消息模板
    TPL_RETURN_IMAGE = '''<xml>
<ToUserName><![CDATA[{TOUSER}]]></ToUserName>
<FromUserName><![CDATA[{FROMUSER}]]></FromUserName>
<CreateTime>{TIME}</CreateTime>
<MsgType><![CDATA[image]]></MsgType>
<Image>
<MediaId><![CDATA[{MEDIA_ID}]]></MediaId>
</Image>
</xml>'''
    # 统一下单模板
    TPL_UNIFIED_ORDER = '''<xml>
   <appid><![CDATA[{appid}]]</appid>
   <attach><![CDATA[{attach}]]</attach>
   <body><![CDATA[{body}]]</body>
   <detail><![CDATA[{detail}]]</detail>
   <mch_id><![CDATA[{mch_id}]]</mch_id>
   <nonce_str><![CDATA[{nonce_str}]]</nonce_str>
   <notify_url><![CDATA[{notify_url}]]</notify_url>
   <openid><![CDATA[{openid}]]</openid>
   <out_trade_no><![CDATA[{out_trade_no}]]</out_trade_no>
   <spbill_create_ip><![CDATA[{spbill_create_ip}]]</spbill_create_ip>
   <total_fee><![CDATA[{total_fee}]]</total_fee>
   <trade_type><![CDATA[{trade_type}]]</trade_type>
   <trade_expire><![CDATA[{trade_expire}]]</trade_expire>
   <time_start><![CDATA[{time_start}]]</time_start>
   <device_info><![CDATA[{device_info}]]</device_info>
   <fee_type><![CDATA[{fee_type}]]</fee_type>
   <goods_tag><![CDATA[{goods_tag}]]</goods_tag>
   <product_id><![CDATA[{product_id}]]</product_id>
   <limit_pay><![CDATA[{limit_pay}]]</limit_pay>
   <sign><![CDATA[{sign}]]</sign>
</xml>'''

    def __init__(self, loop, ch):
#-#        self.APPID = conf['wx_appid'].encode('utf8')
#-#        self.APPSECRET = conf['wx_appsecret'].encode('utf8')
#-#        self.TOKEN = conf['wx_token'].encode('utf8')
#-#        self.ENCODINGAESKEY = conf['wx_encodingaeskey'].encode('utf8')
        self.APPID = conf['wx_appid']
        self.APPSECRET = conf['wx_appsecret']
        self.TOKEN = conf['wx_token']
        self.ENCODINGAESKEY = conf['wx_encodingaeskey']
        resolver = AsyncResolver(nameservers=['8.8.8.8', '8.8.4.4'])
        conn = aiohttp.TCPConnector(resolver=resolver, limit=10)
        self.loop = loop
        if self.loop:
            self.sess = aiohttp.ClientSession(connector=conn, headers={'User-Agent': conf['user_agent']}, loop=self.loop)
        else:
            self.sess = aiohttp.ClientSession(connector=conn, headers={'User-Agent': conf['user_agent']})
        self.ch = ch  # CommonHandler 实例 提供 db/cache 支持

    async def clean(self):
        if self.sess:
            await self.sess.close()

    def setCommHandler(self, ch):
        """用于延后设置或中途替换
        """
        self.ch = ch

    async def getAccessToken(self):
        """取access token
        """
        access_token = None
        r = await self.ch.getCache()
        c_k = '_Z_WX_ACCESS_TOKEN'
        access_token = await r.getObj(c_k)
        if access_token is None:
            url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}'.format(APPID=self.APPID, APPSECRET=self.APPSECRET)
            try:
                resp = await self.sess.get(url)
                j_data = await resp.json()
            except:
                error('', exc_info=True)
            else:
                if 'errcode' in j_data:
                    info('errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
                else:
                    access_token = j_data['access_token']
                    expires_in = j_data['expires_in']
                    info('access token[:20]%s expire in %s', access_token[:20], expires_in)
                    await r.setObj(c_k, access_token, expires_in)
        else:
            info('cache hit %s', c_k)

        return access_token

    async def getIpList(self):
        """取微信服务器ip列表
        """
        ip_list = []

        r = await self.ch.getCache()
        c_k = '_Z_WX_IP_LIST'
        ip_list = await r.getObj(c_k)
        if ip_list is None:
            access_token = await self.getAccessToken()
            if access_token:
                url = 'https://api.weixin.qq.com/cgi-bin/getcallbackip?access_token={ACCESS_TOKEN}'.format(ACCESS_TOKEN=access_token)
                try:
                    resp = await self.sess.get(url)
                    j_data = await resp.json()
                except:
                    error('', exc_info=True)
                else:
                    if 'errcode' in j_data:
                        info('errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
                        # 出错情况下 5秒内不重试
                        await r.setObj(c_k, ip_list, 5)
                    else:
                        ip_list = j_data['ip_list']
#-#                        info('ip_list: %s', ip_list)
                        await r.setObj(c_k, ip_list, 3600)
            else:
                info('can\'t get access_token, no ip list returned.')
        else:
            info('cache hit %s', c_k)

        return ip_list

    def createText(self, nonce, encrypt_type, from_user, to_user, content):
        u'''构造文本消息

        ``content`` 为文本内容
        '''
        ret_data = b'success'
        to_xml = WXManager.TPL_RETURN_TEXT.format(TOUSER=from_user, FROMUSER=to_user, TIME=int(time.time()), CONTENT=content)
#-#        info('to_xml %s', to_xml)
#-#        info('encrypt_type %s', encrypt_type)
        if encrypt_type == 'aes':
            encryp_helper = WXBizMsgCrypt(self.TOKEN, self.ENCODINGAESKEY, self.APPID)
            ret, encrypt_xml = encryp_helper.EncryptMsg(to_xml, nonce)
            if not ret:
#-#                info('encrypt_xml %s', encrypt_xml)
                ret_data = encrypt_xml
            else:
                info('加密失败 %s %s', ret, encrypt_xml)
        return ret_data

    def createImage(self, nonce, encrypt_type, from_user, to_user, media_id):
        u'''构造图片消息

        ``media_id`` 为图片素材id
        '''
        ret_data = 'success'
        to_xml = WXManager.TPL_RETURN_IMAGE.format(TOUSER=from_user, FROMUSER=to_user, TIME=int(time.time()), MEDIA_ID=media_id)
        if encrypt_type == 'aes':
            encryp_helper = WXBizMsgCrypt(self.TOKEN, self.ENCODINGAESKEY, self.APPID)
            ret, encrypt_xml = encryp_helper.EncryptMsg(to_xml, nonce)
            if not ret:
                ret_data = encrypt_xml
            else:
                info('加密失败 %s %s', ret, encrypt_xml)
        return ret_data

    def extractXml(self, nonce, encrypt_type, msg_sign, timestamp, from_xml):
        u'''解析接收的消息，以字典形式返回
        '''
        d_data = ''
#-#        info('nonc %s encrypt_type %s msg_sign %s timestamp %s', nonce, encrypt_type, msg_sign, timestamp)
#-#        info('raw data: %s', from_xml)
        if encrypt_type == 'aes':
            decrypt_helper = WXBizMsgCrypt(self.TOKEN, self.ENCODINGAESKEY, self.APPID)
            ret, decryp_xml = decrypt_helper.DecryptMsg(from_xml, msg_sign, timestamp, nonce)
            if not ret:
                from_xml = decryp_xml
            else:
                info('解密失败 %s %s', ret, decryp_xml)
                return d_data
        # parse to dict
        if from_xml:
            d_data = parseXml2Dict(from_xml)
#-#            info('接收:\n%s', pcformat(d_data))
        return d_data

    async def getUserInfo(self, openid):
        u'''获取用户基本信息
        '''
        wx_user = None
        access_token = await self.getAccessToken()
        if access_token:
            url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token={ACCESS_TOKEN}&openid={OPENID}&lang=zh_CN'.format(ACCESS_TOKEN=access_token, OPENID=openid)
            try:
                resp = await self.sess.get(url)
                j_data = await resp.json()
            except:
                error('', exc_info=True)
            else:
                if j_data.get('errcode', None):
                    info('获取用户基本信息出错： errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
                else:
                    wx_user = j_data
        else:
            info('can\'t get access_token, no ip list returned.')
        return wx_user

    async def createSelfMenu(self):
        u'''创建自定义菜单

        * True 成功
        * False 失败
        '''
        ret_data = False
        access_token = await self.getAccessToken()
        url = 'https://api.weixin.qq.com/cgi-bin/menu/create?access_token={ACCESS_TOKEN}'.format(ACCESS_TOKEN=access_token)
#-#        data = {'button': [{'type': 'view', 'name': u'快速下载', 'url': 'http://www.hongbaosuoping.com/client_share/download/download.html'},
#-#                           {'type': 'view', 'name': u'自助服务', 'url': 'http://www.hongbaosuoping.com/portal.php?mod=topic&topicid=9'},
#-#                           {'type': 'click', 'name': u'获取验证码', 'key': 'vcode'},
#-#                           ]
#-#                }
        login_cfg = {'APPID': self.APPID,
                     'REDIRECT_URI': quote('http://liveonnet.f3322.net:7777/'),
                     'SCOPE': 'snsapi_userinfo',
                     'STATE': 'login',
                     }
        test_cfg = {'APPID': self.APPID,
                    'REDIRECT_URI': quote('http://weixin.aa123bb.com/wx_auth'),
                    'SCOPE': 'snsapi_userinfo',
                    'STATE': 'test',
                    }
        data = {'button': [{'name': u'菜单',
                            'sub_button': [{'type': 'view',
                                            'name': '商城',
                                            'url': 'https://open.weixin.qq.com/connect/oauth2/authorize?appid={APPID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}&state={STATE}#wechat_redirect'.format(**login_cfg)
                                            },
                                           {'type': 'view',
                                            'name': 'test',
                                            'url': 'https://open.weixin.qq.com/connect/oauth2/authorize?appid={APPID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}&state={STATE}#wechat_redirect'.format(**test_cfg)
                                            },
                                           {'type': 'click',
                                            'name': '二维码',
                                            'key': 'qc_subscribe'
                                            },
                                           {'type': 'click',
                                            'name': '不存在',
                                            'key': 'not_exist'
                                            },
                                           ]
                            },
                           {'type': 'view',
                            'name': u'快速下载',
                            'url': 'http://cn.bing.com/'
                            },
                           {'type': 'view',
                            'name': u'自助服务',
                            'url': 'http://m.baidu.com/'
                            },
                           ]
                }
#-#        info('url: %s', url)  # debug only
#-#        info('body: %s', json.dumps(data))
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
        except:
            error('', exc_info=True)
        else:
            if j_data['errcode']:
                info('创建菜单出错: errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
            else:
                ret_data = True
        return ret_data

    async def getSelfMenu(self):
        u'''获取自定义菜单配置

        * 成功则返回json格式菜单配置信息
        * 失败则返回 None
        '''
        ret_data = None
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/cgi-bin/get_current_selfmenu_info?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        info('url: %s', url)
        try:
            resp = await self.sess.get(url)
            j_data = await resp.json()
            ret_data = j_data
        except:
            error('', exc_info=True)
        return ret_data

    async def sendTplMsg(self, tpl_id, openid, url, in_data):
        u'''发送模板消息

        * True 成功
        * False 失败
        '''
        ret_data = False
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        data = {'touser': openid,
                'template_id': tpl_id,
                'url': url,
                'data': in_data,
                }
        info('url: %s', url)
        info('data: %s', pcformat(data))
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
        except:
            error('', exc_info=True)
        else:
            if j_data['errcode']:
                info('发送模板消息出错: errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
            else:
                ret_data = True
        return ret_data

    async def getMediaId(self, media_type, media_data, key):
        u'''获取素材id
        * ``media_type`` 素材类型 image/voice/video/thumb 之一
        * ``media_data`` 素材数据，如果 ``media_data`` 不为空 且 ``key`` 在缓存中查不到，则上传素材
        * ``key`` 指定的key值，以后可以设置 ``media_data`` 为空的情况下获取已经上传的素材id

        返回 media_id ，此数值可以用于构造图片消息
        '''
        media_id = None
        d_content_type = {'image': 'image/jpg',  # bmp/png/jpeg/jpg/gif
                          'voice': 'voice/mp3',  # mp3/wma/wav/amr
                          'video': 'video/mp4',
                          'thumb': 'thumb/jpg',
                          }
        if media_type not in d_content_type:
            info('unknown media_type %s', media_type)
            return media_id

        if not key:
            if not media_data:
                info('media_data 为空')
                return media_id
            key = md5(media_data).hexdigest()

        c_k = '_Z_WX_M_%s_%s' % (media_type, key)
        r = await self.ch.getCache()
        media_id = await r.getObj(c_k)
        if not media_id:
            if not media_data:  # 缓存里面没有查到，必须先上传，media_type必须非空
                info('media_data 为空')
                return media_id

            access_token = await self.getAccessToken()
            url = 'https://api.weixin.qq.com/cgi-bin/media/upload?access_token={ACCESS_TOKEN}&type={MEDIA_TYPE}'.format(ACCESS_TOKEN=access_token, MEDIA_TYPE=media_type)
#-#            info('url: %s', url)  # debug only
            nr_try = 1
            while 1:
                boundary = ''.join((random.choice(string.digits) for _ in xrange(32)))
                if media_data.find(boundary) == -1:
                    break
                nr_try += 1
            headers = {'Content-Type': 'multipart/form-data;boundary=%s' % boundary}
            form_body = '--%s\r\n' \
                        'Content-Disposition: form-data; name="media"; filename="upload.%s"\r\n' \
                        'Content-Type: %s\r\n' \
                        'FileLength: %s\r\n\r\n' \
                        '%s\r\n' \
                        '--%s--\r\n' \
                        % (boundary, d_content_type[media_type].split('/')[1], d_content_type[media_type], len(media_data), media_data, boundary)
#-#            info('form_body(header part):\n%s', form_body[:form_body.find('\r\n\r\n')])  # debug only
            try:
                resp = await self.sess.post(url, data=form_body, headers=headers)
                j_data = await resp.json()
            except:
                error('', exc_info=True)
            else:
                if j_data.get('errcode', None):
                    info('上传素材出错: errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
                else:
                    media_id = j_data['media_id']
                    await r.setObj(c_k, media_id, 86400 * 3)
        else:
            info('cache hit %s', c_k)

        return media_id

    async def getOAuthAccessTokenOpenId(self, code):
        u'''通过code换取网页授权access_token 和 openid

        '''
        access_token, openid = None, None
        r = await self.ch.getCache()
        c_k = '_Z_WX_O_ACCESS_TOKEN_%s' % code
        c_data = await r.getObj(c_k)
        if c_data is None:
            url = 'https://api.weixin.qq.com/sns/oauth2/access_token?appid={APPID}&secret={APPSECRET}&code={CODE}&grant_type=authorization_code'.format(APPID=self.APPID, APPSECRET=self.APPSECRET, CODE=code)
            try:
                resp = await self.sess.get(url)
                j_data = await resp.json()
            except:
                error('', exc_info=True)
            else:
                if 'errcode' in j_data:
                    info('errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
                else:
                    access_token = j_data['access_token']
                    expires_in = j_data['expires_in']
                    openid = j_data['openid']
    #-#                scope = j_data['scope']
    #-#                unionid = j_data.get('unionid', '')
                    info('access token[:20]%s expire in %s openid %s', access_token[:20], expires_in, openid)
                    await r.setObj(c_k, (access_token, openid), expires_in)
        else:
            info('cache hit %s', c_k)
            access_token, openid = c_data

        return access_token, openid

    async def getOAuthUserInfo(self, access_token, openid):
        """取用户信息(需scope为 snsapi_userinfo)
        **参数**
         * ``access_token``
         * ``openid``

        **返回**
         * ``openid`` 用户的唯一标识
         * ``nickname`` 用户昵称
         * ``sex`` 用户的性别，值为1时是男性，值为2时是女性，值为0时是未知
         * ``province`` 用户个人资料填写的省份
         * ``city`` 普通用户个人资料填写的城市
         * ``country`` 国家，如中国为CN
         * ``headimgurl`` 用户头像，最后一个数值代表正方形头像大小（有0、46、64、96、132数值可选，0代表640*640正方形头像），用户没有头像时该项为空。若用户更换头像，原有头像URL将失效。
         * ``privilege`` 用户特权信息，json 数组，如微信沃卡用户为（chinaunicom）
         * ``unionid`` 只有在用户将公众号绑定到微信开放平台帐号后，才会出现该字段。详见：获取用户个人信息（UnionID机制）
        """
        wx_user = None
        url = 'https://api.weixin.qq.com/sns/userinfo?access_token={ACCESS_TOKEN}&openid={OPENID}&lang=zh_CN'.format(ACCESS_TOKEN=access_token, OPENID=openid)
        try:
            resp = await self.sess.get(url)
            j_data = await resp.json()
        except:
            error('', exc_info=True)
        else:
            if 'errcode' in j_data:
                info('errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
            else:
                wx_user = j_data

        return wx_user

    async def getOAuthUserInfoByCode(self, code, ch):
        """据code获取用户基本信息
        """
        wx_user = None
        access_token, openid = await self.getOAuthAccessTokenOpenId(code, ch)
        if access_token:
            wx_user = await self.getOAuthUserInfo(access_token, openid)
        return wx_user

    async def checkOAuthAccessToken(self, access_token, openid):
        u'''检查access_token有效性
        '''
        rtn = False
        url = 'https://api.weixin.qq.com/sns/auth?access_token={ACCESS_TOKEN}&openid={OPENID}'.format(ACCESS_TOKEN=access_token, OPENID=openid)
        try:
            resp = await self.sess.get(url)
            j_data = await resp.json()
        except:
            error('', exc_info=True)
        else:
            if j_data['errcode']:
                info('errcode %s, errmsg: %s', j_data['errcode'], j_data.get('errmsg', ''))
            else:
                rtn = True

        return rtn

    async def addKf(self, kf_account, nickname, password):
        u'''添加客服帐号
        '''
        ret_data = None
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/customservice/kfaccount/add?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        info('url: %s', url)
        data = {'kf_account': kf_account,
                'nickname': nickname,
                'password': password
                }
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
            ret_data = j_data
        except:
            error('', exc_info=True)
        return ret_data

    async def updKf(self, kf_account, nickname, password):
        """改客服帐号
        """
        ret_data = None
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/customservice/kfaccount/update?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        info('url: %s', url)
        data = {'kf_account': kf_account,
                'nickname': nickname,
                'password': password
                }
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
            ret_data = j_data
        except:
            error('', exc_info=True)
        return ret_data

    async def delKf(self, kf_account, nickname, password):
        """除客服帐号
        """
        ret_data = None
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/customservice/kfaccount/del?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        info('url: %s', url)
        data = {'kf_account': kf_account,
                'nickname': nickname,
                'password': password
                }
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
            ret_data = j_data
        except:
            error('', exc_info=True)
        return ret_data

    async def kfSendMsg(self, msg_data):
        """发消息 不需要直接调用
        """
        ret_data = None
        access_token = await self.getAccessToken()
        url = '''https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={ACCESS_TOKEN}'''.format(ACCESS_TOKEN=access_token)
        info('url: %s', url)
        data = msg_data
        try:
            resp = await self.sess.post(url, data=json.dumps(data, ensure_ascii=False))
            j_data = await resp.json()
            ret_data = j_data
        except:
            error('', exc_info=True)
        return ret_data

    async def kfSendImageMsg(self, openid, media_id):
        """发送图片消息
        """
        data = {'touser': openid,
                'msgtype': 'image',
                'image': {'media_id': media_id},
                }
        return await self.kfSendMsg(data)

    async def kfSendTextMsg(self, openid, content):
        """发送文本消息
        """
        data = {'touser': openid,
                'msgtype': 'text',
                'text': {'content': content},
                }
        return await self.kfSendMsg(data)

if __name__ == '__main__':
    from lib.handler_lib import CommonHandler

    async def test_main(loop):
        conf['loop'] = loop
        ch = CommonHandler(None, None)
        mgr = WXManager(loop, ch)
#-#        pass
#-#        yield WXManager.sendTplMsg(TPL_SEND_VC, 'owD3VszZ1r115U-DVYLMdCWU1AVE', '',
#-#                                   {'first': {'value': u'尊敬的用户'}, 'number': {'value': str(random.randint(1000, 9999)), 'color': '#FF3300'}, 'remark': {'value': u'该验证码有效期30分钟可输入1次，转发无效。'}})

#-#        pic_data = yield WXManager.getQrPicBySceneId(1)
#-#        open('/tmp/t.jpg', 'wb').write(pic_data)

#-#        pic_data = open('/tmp/t.jpg', 'rb').read()
#-#        media_id = yield WXManager.getMediaId('image', pic_data, 'test_qr')

#-#        image_data, ticket, expire_at = yield WXManager.getQrPicBySceneId(1)
#-#        media_id = await mgr.getMediaId('image', None, key='qrcode_subs')
#-#        info('media_id %s', media_id)
#-#        r = await mgr.kfSendImageMsg('olQcFt_RHZqgL9CyNuDuyy21hhKg', media_id)
#-#        info('r: %s', r)

#-#        mgr.getAccessToken()
#-#        r = await mgr.getIpList()
        r = await mgr.createSelfMenu()
        info('r: %s', pcformat(r))
        await mgr.clean()
        info('ch %s', ch)
        ch.clean()
#-#        mgr.getSelfMenu()

    loop = asyncio.get_event_loop()
    try:
        task = asyncio.ensure_future(test_main(loop))
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        info('cancel on KeyboardInterrupt..')
        task.cancel()
        loop.run_forever()
        task.exception()
    finally:
        loop.stop()
    sys.exit(0)

