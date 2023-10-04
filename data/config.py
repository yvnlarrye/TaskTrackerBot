from utils.utils import get_json_file_contents

CONFIG = get_json_file_contents('data/config.json')
PASS = CONFIG['password']
REQUEST_STATUS = CONFIG['request_status']

