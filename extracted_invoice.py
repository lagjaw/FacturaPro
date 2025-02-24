import json

def save_to_json(data, filename='extracted_invoice.json'):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)
