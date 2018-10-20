from resela.app import DATABASE as db

user_vlan = db.Table('user_vlans',
                     db.Column('user_id', db.String(32), db.ForeignKey('user.user_id')),
                     db.Column('vlan_id', db.Integer, db.ForeignKey('vlan.vlan_id'))
)
