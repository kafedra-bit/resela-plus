from keystoneauth1.identity import v3
from keystoneauth1 import session, exceptions
from neutronclient.v2_0 import client as NeutronClient
from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.projects import ProjectManager

import sys

if len(sys.argv) != 3:
    print("Expected username and password")
    quit(1)

aut = v3.Password(auth_url='http://controller:35357/v3', username=sys.argv[1], password=sys.argv[2],
                  project_name='Default', project_domain_name='Default', user_domain_name='Default')
sess = session.Session(auth=aut)
keystone_client = KeystoneClient(session=sess)
project_manager = ProjectManager(keystone_client)
neutron_client = NeutronClient.Client(session=sess)

security_groups = neutron_client.list_security_groups()
for group in security_groups['security_groups']:
    try:
        project_manager.get(group['tenant_id'])
    # TODO Verify that this actually works to remove old security groups
    except exceptions.NotFound:
        neutron_client.delete_security_group(group['id'])
    except Exception as e:
        print(e)
