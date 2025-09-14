def load_json_settings(config_file):
    import json
    with open(config_file, 'rb') as f:
        return json.load(f)


def update_json_settings(config_file, new_data):
    import json
    with open(config_file, 'rb') as f:
        data = json.load(f)
    data.update(new_data)
    with open(config_file, 'wb') as f:
        json.dump(data, f)
