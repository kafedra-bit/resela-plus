#!/usr/bin/python3

import hashlib
import binascii
import sys
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

if len(sys.argv) != 2:
    print("Expected password")
    quit(1)

aut = v3.Password(auth_url='http://controller:35357/v3', username='admin', password=sys.argv[1],
                  project_name='default', project_domain_name='default', user_domain_name='default')
sess = session.Session(auth=aut)
ks = client.Client(session=sess)
admin_user = ks.users.find(name='admin')
ks.users.update(admin_user, first_name='Bosse', last_name='Bossesson')
