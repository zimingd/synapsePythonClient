import os
import json
import platform
import stat
from contextlib import closing

SESSION_FILENAME = '.synapseSession'
SESSION_FILEPATH = os.path.join(os.path.expanduser('~'), SESSION_FILENAME)
IS_WINDOWS = False

if platform.system() == "Windows":
    IS_WINDOWS = True
    import win32security
    import win32api
    import win32file
    import ntsecuritycon as con


def compare_windows_security_descriptor(expected_sd, actual_sd):
    return False #TODO: implement later

class open_file_checking_permission(object):
    """
    context manager that has the same functionality as open()
    but also performs a check on the opened file's permissions.
    If the permissions on that file are not 0o600(user read/write only) , the file will be DELETED and a new fill will be created to replace it.
    :param name:
    :param mode:
    :param buffering:
    :return: file object
    """
    def __init__(self, name, mode=None, buffering=None):
        self.name = name
        self.mode = mode
        self.buffering = buffering
        self.expected_POSIX_permission = 0o600

    def __enter__(self):
        try:
            self.check_file_permissions()
        except OSError:
            #file does not exist, which is fine
            pass

        self.opened_file = open(self.name, mode=self.mode, buffering=self.buffering)
        return self.opened_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.opened_file.close()

    def check_file_permissions(self):
        if IS_WINDOWS:
            self.check_file_permission_windows()
        else:
            self.check_file_permissions_POSIX()


    def check_existing_file_permissions(self, expected_security_descriptor):
        sd = win32security.GetFileSecurity(self.name, win32security.DACL_SECURITY_INFORMATION)
        return compare_windows_security_descriptor(expected_security_descriptor, sd)

    def check_file_permission_windows(self):
        """Windows y u do dis?"""
        # Modified version code example in:
        # http://timgolden.me.uk/python/win32_how_do_i/add-security-to-a-file.html


        #generate wanted security desciptor
        # get user id of the current user; domain and type are not used
        user, domain, type = win32security.LookupAccountName("", win32api.GetUserName())
        attributes = win32security.SECURITY_ATTRIBUTES()
        attributes.bInheritHandle=False

        #AHHHH MY BRAIN HURTS
        expected_security_descriptor = attributes.SECURITY_DESCRIPTOR
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE, user)
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa379583(v=vs.85).aspx
        expected_security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)


        if not os.path.exists(self.name) or self.check_existing_file_permissions(expected_security_descriptor):
            #create a file
            #https://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx
            with closing(win32file.CreateFile(self.name,
                                 win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                 win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                 attributes,
                                 win32file.CREATE_ALWAYS,
                                 win32file.FILE_ATTRIBUTE_NORMAL,
                                 None)) as pyfh:
                win32file.WriteFile(pyfh, "{}\n".encode())



    def check_file_permissions_POSIX(self):
        """Checks for permission of 0o600 (-rw-------) and if permission does not match, replace with new file"""
        curr_permissions_octal = stat.S_IMODE(os.stat(self.name).st_mode)

        #permissions do not match so delete the old one and create a new one
        if curr_permissions_octal != self.expected_POSIX_permission:
            os.remove(self.name)
            # os.open allows creation of a file with permissions already set, which the default open() does not support
            with os.fdopen(os.open(self.name, os.O_CREAT | os.O_WRONLY, self.expected_POSIX_permission), 'w') as fh:
                fh.write("{}\n")


def _readSessionCache():
    """Returns the JSON contents of CACHE_DIR/SESSION_FILENAME."""
    try:
        with open_file_checking_permission(SESSION_FILEPATH, 'r') as file:
            result = json.load(file)
            if isinstance(result, dict):
                return result
    except:
        pass
    return {}


def _writeSessionCache(data):
    """Dumps the JSON data into CACHE_DIR/SESSION_FILENAME."""
    with open_file_checking_permission(SESSION_FILEPATH, 'w') as file:
        json.dump(data, file)
        file.write('\n')  # For compatibility with R's JSON parser



def _remove_old_session_file(old_sesion_filepath):
    """This deletes the old .session file left over in the users cache"""
    try:
        os.remove(old_sesion_filepath)
    except OSError:
        # ignore if it does not exist
        pass
