# Copyright 2015 Cisco Systems, Inc.
# Copyright 2018 Tomas Hlavacek (tmshlvck@gmail.com)
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import password
db_host=password.db_host
db_name=password.db_name
db_user=password.db_user
db_passwd=password.db_passwd

import sys
import os

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                                    os.pardir,os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'yabmp', '__init__.py')):
    sys.path.insert(0, possible_topdir)
else:
    possible_topdir = '/'


from Queue import Queue
from threading import Thread
import time
import logging
import psycopg2
from oslo_config import cfg
from yabmp.handler import BaseHandler
from yabmp.channel.publisher import Publisher
from yabmp.channel import config as channel_config
from yabmp.service import prepare_service


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

q = Queue()

def dbconn():
    return 'host=%s dbname=%s user=%s password=%s' % (db_host, db_name, db_user, db_passwd)


def dbselect(select):
    conn = psycopg2.connect(dbconn())
    cur = conn.cursor()
    cur.execute(select)
    for r in cur:
        yield r
    # conn.commit()
    cur.close()
    conn.close()


def db_write():
    while(True):
        msg = None
        try:
            conn = psycopg2.connect(dbconn())
            while(True):
                cur = conn.cursor()
                i = 0
                while(i<1000):
                    msg = q.get()
                    if 'attr' in msg and msg['attr']:
                        attr = msg['attr']
                        nlri = msg['nlri']
                        orig = int(attr[2][0][1][-1])

                        for n in nlri:
                            cur.execute("INSERT INTO local_announcements (asn, prefix) values (%s, %s) on conflict (asn, prefix) do update set updated_at = now();", (orig, n))
                            i+=1
                    for w in msg['withdraw']:
                        cur.execute("DELETE FROM local_announcements where asn = %s and prefix = %s;", (orig, n))
                        i+=1
                conn.commit()
                cur.close()
        except KeyboardInterrupt:
            return
        except Exception as e:
            if msg:
                print("exc=%s msg=%s"%(str(e),str(msg)))
            else:
                print("exc=%s"%str(e))
            if conn:
                conn.close()


class ReHandler(BaseHandler):
    def __init__(self):
        super(ReHandler, self).__init__()

    def init(self):
        print

    def on_message_received(self, peer_host, peer_port, msg, msg_type):
        """process for message received
        """
        if msg_type == 0:
            if msg[1][0] == 2: # msg_mtype
                q.put(msg[1][1]) 
    def on_connection_made(self, peer_host, peer_port):
        pass

    def on_connection_lost(self, peer_host, peer_port):
        pass




def main():
    Thread(target=db_write).start()
    try:
        handler = ReHandler()
        prepare_service(handler=handler)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    sys.exit(main())

