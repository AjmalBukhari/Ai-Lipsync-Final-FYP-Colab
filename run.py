import os
from flask_migrate import Migrate
from flask_minify  import Minify
from sys import exit

from apps.config import config_dict
from apps import create_app, db

from pyngrok import ngrok
import subprocess, logging


# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# Set log level to WARNING to suppress info and debug messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:

    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]

except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app(app_config)
migrate = Migrate(app, db)

if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)
    
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG)             )
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE' )
    app.logger.info('DBMS             = ' + app_config.SQLALCHEMY_DATABASE_URI)
    app.logger.info('ASSETS_ROOT      = ' + app_config.ASSETS_ROOT )



# Kill any existing ngrok processes to reset before starting a new tunnel
subprocess.call(['pkill', 'ngrok'])

# Set your ngrok authentication token (replace with your actual token)
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "63Rprg8vfopGku86TmQz7_5B1i8o1FQqwwKs6N6ucwV")
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# Define your reserved domain (replace with your actual domain)
RESERVED_DOMAIN = os.getenv("NGROK_RESERVED_DOMAIN", "insect-intimate-terribly.ngrok-free.app")

# Open a tunnel with the reserved domain
ngrok_tunnel = ngrok.connect(addr="5000", host_header="rewrite", domain=RESERVED_DOMAIN)
app.logger.info("ngrok tunnel \"{}\" -> \"http://127.0.0.1:5000\"".format(ngrok_tunnel.public_url))

if __name__ == "__main__":
    app.run()
