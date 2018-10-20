from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
import sys

if len(sys.argv) != 3:
    print("Expected username and password")
    quit(1)

aut = v3.Password(auth_url='http://controller:35357/v3', username=sys.argv[1], password=sys.argv[2],
                  project_name='Default', project_domain_name='Default', user_domain_name='Default')
sess = session.Session(auth=aut)
keystone = client.Client(session=sess)
image_library = keystone.domains.find(name='imageLibrary')
keystone.projects.create(name='imageLibrary|default', domain=image_library,
                         description='This project holds the default images that uploaded and '
                                     'administrated by admins', img_list=[])
keystone.projects.create(name='imageLibrary|snapshots', domain=image_library,
                         description='This project holds the snapshots created in ReSeLa and '
                                     'uploaded from a user', img_list=[])
keystone.projects.create(name='imageLibrary|images', domain=image_library,
                         description="This project holds the images that's not a default image "
                                     "nor a snapshot", img_list=[])
