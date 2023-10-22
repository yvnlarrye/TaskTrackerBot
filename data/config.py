import json


def get_json_file_contents(file_name: str) -> dict:
    json_file = open(file_name, encoding='utf-8')
    json_data = json.load(json_file)
    json_file.close()
    return json_data


def get():
    return get_json_file_contents('data/config.json')


CONFIG = get_json_file_contents('data/config.json')
PASS = CONFIG['password']
REQUEST_STATUS = CONFIG['request_status']
STATUS = CONFIG['status']

