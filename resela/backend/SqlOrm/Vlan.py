from resela.app import DATABASE as db


class Vlan(db.Model):
    vlan_id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.String(32))

    def __init__(self, vlan=None, lab_id=None):
        self.vlan_id = vlan
        self.lab_id = lab_id
