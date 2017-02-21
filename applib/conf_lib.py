import pathlib
import yaml
#-#from applib.tools_lib import pcformat
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning

# load config from yaml file in current dir
conf_file_path = str(pathlib.Path('.') / 'config' / 'server.yaml')
conf = yaml.load(open(conf_file_path))
