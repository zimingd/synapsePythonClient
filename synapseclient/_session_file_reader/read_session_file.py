import os
import json
from .open_file_with_permission_check import open_file_and_ensure_permissions
SESSION_FILENAME = '.synapseSession'
SESSION_FILEPATH = os.path.join(os.path.expanduser('~'), SESSION_FILENAME)


def readSessionCache():
    """Returns the JSON contents of CACHE_DIR/SESSION_FILENAME."""
    try:
        with open_file_and_ensure_permissions(SESSION_FILEPATH, 'r') as file:
            result = json.load(file)
            if isinstance(result, dict):
                return result
    except:
        pass
    return {}


def writeSessionCache(data):
    """Dumps the JSON data into CACHE_DIR/SESSION_FILENAME."""
    with open_file_and_ensure_permissions(SESSION_FILEPATH, 'w') as file:
        json.dump(data, file)
        file.write('\n')  # For compatibility with R's JSON parser

