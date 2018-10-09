import json
import logging
import re
import time
import sys
import threading
import itchat
from itchat.content import *



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

    def __init__(self,userid=None, roomid=None):
        self._userid = userid
        self._roomid = roomid

    @property
    def userid(self):
        return self._userid

    @property
    def username(self):
        user = self._userid
        return user

    @property
    def roomid(self):
        return self._roomid

    client = roomid
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
        self.usrname=None
        #itchat.login()
        itchat.auto_login()
        self.roomlist,self.myfrilist=self.friendlist()
        log.info(self.myfrilist)
    def friendlist(self):
        qun,users=itchat.get_contact(update=True)
        return qun,users


    def msg_event_handler(self,msg):
        if msg and msg != None:
            for i in msg:
                mess={}
                #if i['ToUserName'].startswith('@@'):
                #    mess['frm']=i['ToUserName']
                #    mess['to']=i['FromUserName']
                #    mess['content']=i['Content']
                #else:
                mess['frm']=i['FromUserName']
                mess['to']=i['ToUserName']
                mess['content']=i['Content']
                log.info(mess)
                self.build_msg(mess)
            
    def process_mentions(self,text):
        pass
    def build_msg(self,msg):
        text=msg['content']
        user=msg['frm']
        touser=msg['to']
        for i in self.myfrilist:
            if i["UserName"]==user:
                user=i["NickName"]
                log.info(i["NickName"])
        log.info(user)
        msgs=Message(text)
        msgs.frm=wechatPerson(user)
        if touser.startswith('@@'):
            self.usrname=touser
        else:
            self.usrname=user
        log.info('ssssssssssssssss %s'%msgs)
        self.callback_message(msgs)

    def serve_once(self):
        log.info("Verifying authentication token")
        myname=itchat.search_friends()
        #log.info(myname)
        self.bot_identifier = wechatPerson(myname['NickName'])
        self.connect_callback()
        self.reset_reconnection_count()
        try:
            while True:
                a,b=itchat.get_msg()
                self.msg_event_handler(a)
        except KeyboardInterrupt:
            log.info("Interrupt received, shutting down..")
            return True
        except Exception:
            log.exception("Error reading from RTM stream:")
        finally:
            log.debug("Triggering disconnect callback")
            self.disconnect_callback()
    def send_message(self, msg):
        super().send_message(msg)
        body=msg.body
        log.debug(body)
        log.debug(self.usrname)
        itchat.send(body,toUserName=self.usrname)
        itchat.send(body,toUserName='filehelper')
        log.debug('sended')
        #for i in self.myfrilist:
        #    if i["UserName"]==self.usrname:
        #        myfriend=itchat.search_friends(nickName=i["NickName"])[0]
        #        myfriend.send(body)
        #        log.info('sended')

    def message_cut(self,msg):
        c=300
        msgs = [msg[i:i+c] for i in range(0,len(msg),c)]
        return msgs


    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        super(QqBackend, self).change_presence(status=status, message=message)


    def build_identifier(self, txtrep:str):
        log.debug("building an identifier from %s" % txtrep)
        #if txtrep.startswith('!'):
        #for i in self.myfrilist:
        #    if i["UserName"]==user:
        #        user_name=i["NickName"]
        #    else:
        #        user_name=user
        users=txtrep
        return wechatPerson(userid=users)


    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        response.to = msg.frm
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
        #print (groupsid)
        #print ([QqRoom(gid=gid, bot=self) for gid in groupsid.keys()])
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
