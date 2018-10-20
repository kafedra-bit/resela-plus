from resela.app import DATABASE as db
from resela.backend.SqlOrm.join_tables import user_vlan


class User(db.Model):
    user_id = db.Column(db.String(32), primary_key=True)
    active_vlan = db.Column(db.Integer, db.ForeignKey('vlan.vlan_id'), unique=True)
    vlans = db.relationship('Vlan', secondary=user_vlan)

    def __init__(self, user_id=None, active_vlan=None):
        self.user_id = user_id
        self.active_vlan = active_vlan
