import os
import json
SESSION_FILENAME = '.synapseSession'
SESSION_FILEPATH = os.path.join(os.path.expanduser('~'), SESSION_FILENAME)


def _readSessionCache():
    """Returns the JSON contents of CACHE_DIR/SESSION_FILENAME."""
    try:
        with open(SESSION_FILEPATH, 'r') as file:
            result = json.load(file)
            if isinstance(result, dict):
                return result
    except:
        pass
    return {}


def _writeSessionCache(data):
    """Dumps the JSON data into CACHE_DIR/SESSION_FILENAME."""
    with open(SESSION_FILEPATH, 'w') as file:
        json.dump(data, file)
        file.write('\n')  # For compatibility with R's JSON parser


def _remove_old_session_file(old_sesion_filepath):
    """This deletes the old .session file left over in the users cache"""
    try:
        os.remove(old_sesion_filepath)
    except OSError:
        # ignore if it does not exist
        pass
