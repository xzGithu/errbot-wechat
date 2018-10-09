#author:xzgithu
import logging
import itchat
from itchat.content import *
import os,sys
import signal
import json
import time



from errbot.backends.base import Message, Presence, ONLINE, AWAY, Room, RoomError, RoomDoesNotExistError, \
    UserDoesNotExistError, RoomOccupant, Person, Card, Stream
from errbot.core import ErrBot
from errbot.utils import split_string_after
from errbot.rendering.ansiext import AnsiExtension, enable_format, IMTEXT_CHRS

# Can't use __name__ because of Yapsy
log = logging.getLogger('errbot.backends.wechatslack')

class wechatPerson(Person):
    """
    This class describes a person on Qq's network.
    """

    def __init__(self,userid=None,clientid=None):
        self._userid = userid
        self._clientid = clientid

    @property
    def userid(self):
        return self._userid

    @property
    def username(self):
        user = self._userid
        return user

    @property
    def clientid(self):
        return self._clientid

    client = clientid
    nick = username

    # Override for ACLs
    @property
    def aclattr(self):
        # Note: Don't use str(self) here because that will return
        # an incorrect format from SlackMUCOccupant.
        return "%s" % self.username

    @property
    def fullname(self):
        user = self._userid
        return user

    def __unicode__(self):
        return "%s" % self.username

    def __str__(self):
        return self.__unicode__()


    def __hash__(self):
        return self.userid.__hash__()

    @property
    def person(self):
        return "%s" % self.username


class wechatRoomOccupant(RoomOccupant, wechatPerson):
    """
    This class represents a person inside a MUC.
    """
    def __init__(self, sc, userid, roomid, bot):
        super().__init__(sc, userid, roomid)
        self._room = QqRoom(gid=roomid, bot=bot)

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return "#%s/%s" % (self._room.name, self.username)

    def __str__(self):
        return self.__unicode__()
class wechatBackend(ErrBot):
    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.adminuser = config.BOT_ADMINS
        self.usrname=None
        itchat.auto_login(hotReload=True)
        self.roomlist,self.myfrilist=self.friendlist()
    def friendlist(self):
        qun,users=itchat.get_contact(update=True)
        return qun,users

    def msg_event_handler(self,msg):
        mess={}
        mess['frm1']=msg['FromUserName']
        mess['to']=msg['ToUserName']
        mess['content']=msg['Content']
        try:
            aaa=itchat.search_friends(userName=mess['frm1'])
            mess['frm']=aaa["NickName"]
            mess['send']=aaa["RemarkName"] if aaa["RemarkName"] else aaa["NickName"]
        except TypeError:
		    try:
                chatroom=itchat.search_chatrooms(userName=mess['frm1'])
                mess['frm']=chatroom["NickName"]
                roommem=itchat.search_friends(userName=msg["ActualUserName"])
                mess['send']=roommem["RemarkName"] if roommem["RemarkName"] else roommem["NickName"]
            except:
                mess['frm']=msg['FromUserName']
                mess['send']="notfriend"
        log.info(mess)
        self.build_msg(mess)
            
    def process_mentions(self,text):
        pass
    def build_msg(self,msg):
        text=msg['content']
        user=msg['frm']
        sendu=msg['send']
        ttuser=msg['frm1']
        touser=msg['to']
        msgs=Message(text)
        msgs.frm=wechatPerson(sendu,touser)
        self.usrname=ttuser
        if ttuser.startswith('@@'):
            msgs.to=wechatPerson(userid=ttuser)
            msgs.id="group"
        else:
            msgs.to=wechatPerson(userid=ttuser)
            msgs.id="user"
        log.info('---------------- %s---------%s' %(msgs.to,msgs.frm))
        log.info('ssssssssssssssss %s'%msgs)
        self.callback_message(msgs)
    def getlogs(self):
        self.logs=None
        @itchat.msg_register(itchat.content.TEXT)
        def wechat_reply(msg):
            self.logs=msg
            #self.msg_event_handler(self.logs)
            if msg.text:
                if "shutdown --confirm" in msg.text:
                    print (self.adminuser)
                    itchat.send("已关闭进程",toUserName=self.adminuser)
                    time.sleep(5)
                    os.kill(os.getpid(), signal.SIGKILL)
            self.msg_event_handler(self.logs)
        @itchat.msg_register(itchat.content.TEXT,isGroupChat=True)
        def wechat_reply(msg):
            self.logs=msg
            self.msg_event_handler(self.logs)
    def serve_once(self):
        log.info("Verifying authentication token")
        #self.connect_callback()
        #self.reset_reconnection_count()
        myname=itchat.search_friends()
        self.bot_identifier = wechatPerson(myname['NickName'])
        self.connect_callback()
        self.reset_reconnection_count()
        try:
            log.info('waiting')
            while True:
                self.getlogs()
                itchat.run()
        #except KeyboardInterrupt:
        #    log.info("Interrupt received, shutting down..")
        #    return True
        except Exception:
            log.exception("Error reading from RTM stream:")
        finally:
            log.debug("Triggering disconnect callback")
            self.disconnect_callback()
    def send_message(self, msg):
        super().send_message(msg)
        body=msg.body
        log.info(msg.frm)
        log.info(msg.to)
        log.debug(body)
        print (msg.to.userid)
        print (type(msg.to.userid))
        toname=msg.to.username
        log.info(toname)
        if msg.to.userid.startswith('@@'):
            itchat.send(body,toUserName=msg.to.userid)
        else:
            try:
                anname=itchat.search_chatrooms(name=toname)
                sendto=anname[0].userName
                itchat.send(body,toUserName=sendto)
            except:
                anname=itchat.search_friends(nickName=toname)
                if anname:
                    sendto=anname[0].userName
                    itchat.send(body,toUserName=sendto)
                else:
                    log.error("没有找到用户或组")
        log.debug('sended')

    def message_cut(self,msg):
        c=300
        msgs = [msg[i:i+c] for i in range(0,len(msg),c)]
        return msgs


    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        super(QqBackend, self).change_presence(status=status, message=message)


    def build_identifier(self, txtrep:str):
        log.debug("building an identifier from %s" % txtrep)
        users=txtrep
        return wechatPerson(userid=users)


    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        log.info('response.frm')
        if msg.to.username.startswith('@@'):
            response.to = msg.to
        else:
            response.to = msg.frm
        log.debug(response.to)
        log.debug(msg)
        log.debug('wwww---resps %s' %response)
        return response
        
    def groupid_to_groupname(self,groupid):
        groupdicts=self.sc.getGroup()
        return groupdicts[groupid]

    def shutdown(self):
        super().shutdown()

    @property
    def mode(self):
        return 'qqslack'

    def query_room(self, room):
        return QqRoom(name=room, bot=self)

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.
        """
        groupsid=self.sc.getGroup()
        return [QqRoom(gid=gid, bot=self) for gid in groupsid.keys()]



class QqRoom(Room):
    def invite(self, *args) -> None:
        log.error('Not implemented')
    @property
    def joined(self) -> bool:
        log.error('Not implemented')
        return True

    def leave(self, reason: str = None) -> None:
        log.error('Not implemented')

    def create(self) -> None:
        log.error('Not implemented')

    def destroy(self) -> None:
        log.error('Not implemented')

    def join(self, username: str = None, password: str = None) -> None:
        log.error('Not implemented')

    @property
    def topic(self) -> str:
        log.error('Not implemented')
        return ''

    @property
    def occupants(self):
        log.error('Not implemented')
        return []
    @property
    def exists(self) -> bool:
        log.error('Not implemented')
        return True

    def __init__(self, name=None ,gid=None, bot=None):
        if name is not None:
            self._name = name
        else:
            self._name = bot.groupid_to_groupname(gid)
        self._bot=bot
        self.sc=bot.sc
    def name(self):
        print (name)
        return self._name

    def __str__(self):
        return "#%s" %self.name
    def __eq__(self, other):
        return other.name == self.name
