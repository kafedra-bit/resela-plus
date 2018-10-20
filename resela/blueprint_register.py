"""

Registers blueprints in flask application

"""

from resela.app import APP

from resela.blueprints.account import account
from resela.blueprints.admin import admin
from resela.blueprints.api import api
from resela.blueprints.default import default
from resela.blueprints.edit import edit
from resela.blueprints.static import static

# Register blueprints
APP.register_blueprint(account)
APP.register_blueprint(admin)
APP.register_blueprint(api)
APP.register_blueprint(default)
APP.register_blueprint(edit)
APP.register_blueprint(static)
