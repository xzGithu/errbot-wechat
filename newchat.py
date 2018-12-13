import logging
import itchat
from itchat.content import *
import os,sys
import signal
import json
import time
import sqlite3



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
    def __init__(self, userid, roomid,):
        super().__init__(userid, roomid)
        self._room = WechatRoom(name=roomid)

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return "%s" % (self._room.name)

    def __str__(self):
        return self.__unicode__()
class wechatBackend(ErrBot):
    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.adminuser = config.BOT_ADMINS
        #self.usrname=None
        itchat.auto_login(hotReload=True)
        self.roomlist,self.myfrilist=self.friendlist()
        #print (self.roomlist)
        #print (self.myfrilist)
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
            mess['room']=mess['send']
        except TypeError:
            try:
                chatroom=itchat.search_chatrooms(userName=mess['frm1'])
                mess['frm']=chatroom["NickName"]
                mess['room']=mess['frm']
                roommem=itchat.search_friends(userName=msg["ActualUserName"])
                mess['send']=roommem["RemarkName"] if roommem["RemarkName"] else roommem["NickName"]
            except:
                chatroom=itchat.search_chatrooms(userName=mess['frm1'])
                mess['room']=chatroom["NickName"]
                mess['frm']=msg['FromUserName']
                mess['send']="notfriend"
        if msg['FromUserName'].startswith('@@'):
            mess['type']='qun'
        else:
            mess['type']='ren'
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
        room=msg['room']
        msgs=Message(text)
        if msg["type"]=="ren":
            msgs.frm=wechatPerson(sendu,touser)
        else:
            msgs.frm=wechatRoomOccupant(userid=sendu,roomid=room)
        #self.usrname=ttuser
        if ttuser.startswith('@@'):
            #msgs.to=wechatPerson(userid=ttuser)
            msgs.to=WechatRoom(name=room)
            msgs.id="group"
            log.info(msgs.to.name)
        else:
            msgs.to=wechatPerson(userid=ttuser)
            msgs.id="user"
        msgs.send=sendu
        log.info('---------------- %s---------%s' %(msgs.to,msgs.frm))
        log.info('ssssssssssssssss %s'%msgs)
        log.info('ssssssssssssssss %s'%msgs.is_group)
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
            if msg.text:
                if "shutdown --confirm" in msg.text:
                    print (self.adminuser)
                    itchat.send("已关闭进程",toUserName=self.adminuser)
                    time.sleep(5)
                    os.kill(os.getpid(), signal.SIGKILL)
            self.msg_event_handler(self.logs)
    def serve_once(self):
        log.info("Verifying authentication token")
        con=sqlite3.connect('/soft/webui/db.sqlite3')
        cur = con.cursor()
        cur.execute("select name from ui_qun")
        rooms=cur.fetchall()
        rooms=[i[0] for i in rooms]
        cur.execute("select descname from ui_person")
        friends=cur.fetchall()
        friends=[i[0] for i in friends]
        myname=itchat.search_friends()
        self.bot_identifier = wechatPerson(myname['NickName'])
        self.connect_callback()
        self.reset_reconnection_count()
        for i in self.roomlist:
            if i['NickName'] not in rooms:
                sql="insert into ui_qun (name) values ('"+i['NickName']+"')"
                cur.execute(sql)
        for i in self.myfrilist:
            if i["RemarkName"] not in friends and i["NickName"] not in friends:
                if i["RemarkName"]!='':
                    sql="insert into ui_person (descname) values ('"+i['RemarkName']+"')"
                else:
                    sql="insert into ui_person (descname) values ('"+i['NickName']+"')"
                cur.execute(sql)
        con.commit()
        con.close()
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
        #print (msg.to.userid)
        #print (type(msg.to.userid))
        try:
            toname=msg.to.username
        except:
            toname=msg.to
        log.info(toname)
        #if msg.to.userid.startswith('@@'):
        #    itchat.send(body,toUserName=msg.to.userid)
        #else:
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
                log.error("没有找到用户或组%s"%toname)
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
        #if msg.to.username.startswith('@@'):
        if msg.id=="group":
            response.to = msg.to.name
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



class WechatRoom(Room):
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

    def __init__(self, name=None ,roomid=None, bot=None):
        self._name = name
    @property
    def name(self):
        print (self._name)
        return self._name

    def __str__(self):
        return self._name
    def __eq__(self, other):
        return other.name == self.name
