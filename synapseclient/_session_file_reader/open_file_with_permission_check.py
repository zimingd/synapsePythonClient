import platform
import stat
import os

from abc import ABCMeta, abstractmethod
from six import with_metaclass

IS_WINDOWS = False
if platform.system() == "Windows":
    IS_WINDOWS = True
    import win32security
    import win32api
    import win32file
    import ntsecuritycon as con


def open_file_and_ensure_permissions(name, mode, buffering=None):
    """
    Context Manager for getting a
    but also performs a check on the opened file's permissions.
    If the permissions on that file are not user read/write only, the file will be DELETED and a new file with correct permissions will be created to replace it.

    :Example:

    with open_file_and_ensure_permissions(filepath, 'w') as file:
        file.write("{}")

    :param name: full path to the file
    :param mode: mode of opening the file. same as the modes used in open()
    :param buffering: same as used in open()
    :return: a context manager that
    """
    if IS_WINDOWS:
        return _OpenFileWithPermissionCheckWindows(name, mode, buffering)
    else:
        return _OpenFileWithPermissionCheckPOSIX(name, mode, buffering)


class _OpenFileWithPermissionCheckAbstractClass(with_metaclass(ABCMeta)):
    def __init__(self, name, mode=None, buffering=None):
        self.name = name
        self.mode = mode
        self.buffering = buffering


    def __enter__(self):

        if not os.path.exists(self.name) or not self.file_permissions_are_correct():
            self.create_new_file_with_correct_permissions()

        self.opened_file = open(self.name, mode=self.mode, buffering=self.buffering)
        return self.opened_file


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.opened_file.close()


    @abstractmethod
    def file_permissions_are_correct(self):
        pass


    @abstractmethod
    def create_new_file_with_correct_permissions(self):
        pass


def compare_windows_security_descriptor_dacls(expected, actual):
    assert expected.GetSecurityDescriptorSacl() == actual.GetSecurityDescriptorSacl()
    assert expected.GetSecurityDescriptorControl() == actual.GetSecurityDescriptorControl()
    assert  expected.GetSecurityDescriptorDacl() ==  actual.GetSecurityDescriptorDacl()
    assert expected.GetSecurityDescriptorGroup() == actual.GetSecurityDescriptorGroup()
    assert expected.GetSecurityDescriptorOwner() == actual.GetSecurityDescriptorOwner()

class _OpenFileWithPermissionCheckWindows(_OpenFileWithPermissionCheckAbstractClass):
    # Modified version code example in:
    # http://timgolden.me.uk/python/win32_how_do_i/add-security-to-a-file.html
    def __init__(self, *args, **kwargs):
        super(_OpenFileWithPermissionCheckWindows, self).__init__(*args, **kwargs)

        # get user id of the current user; domain and type are not used
        user, domain, type = win32security.LookupAccountName("", win32api.GetUserName())

        #generate wanted security desciptor
        self.expected_security_descriptor = win32security.SECURITY_DESCRIPTOR()
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE, user)
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa379583(v=vs.85).aspx
        self.expected_security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0) # args: (bDaclPresent , pDacl , bDaclDefaulted)


    def file_permissions_are_correct(self):
        sd = win32security.GetFileSecurity(self.name, win32security.DACL_SECURITY_INFORMATION)

        return compare_windows_security_descriptor(self.expected_security_descriptor, sd)


    def create_new_file_with_correct_permissions(self):
        attributes = win32security.SECURITY_ATTRIBUTES()
        attributes.bInheritHandle = False
        attributes.SECURITY_DESCRIPTOR = self.expected_security_descriptor

        # create a file with read/write permissions only for the current user
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx
        pyHANDLE = win32file.CreateFile(self.name,
                                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                        attributes,
                                        win32file.CREATE_ALWAYS,
                                        win32file.FILE_ATTRIBUTE_NORMAL,
                                        None)
        pyHANDLE.close()


class _OpenFileWithPermissionCheckPOSIX(_OpenFileWithPermissionCheckAbstractClass):
    def __init__(self, *args, **kwargs):
        super(_OpenFileWithPermissionCheckPOSIX, self).__init__(*args, **kwargs)
        self.expected_POSIX_permission = 0o600


    def file_permissions_are_correct(self):
        curr_permissions_octal = stat.S_IMODE(os.stat(self.name).st_mode)
        return curr_permissions_octal == self.expected_POSIX_permission


    def create_new_file_with_correct_permissions(self):
        # os.remove(self.name) #TODO is this necessary?
        # os.open allows creation of a file with permissions already set, which the default open() does not support
        with os.fdopen(os.open(self.name, os.O_CREAT | os.O_WRONLY, self.expected_POSIX_permission), 'w') as fh:
            pass