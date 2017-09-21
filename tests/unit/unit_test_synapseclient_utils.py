# -*- coding: utf-8 -*-
## unit tests for python synapse client
############################################################
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime as Datetime
from nose.tools import assert_raises, assert_equal
import os, re, sys, inspect

import synapseclient.utils as utils
from synapseclient.activity import Activity
from synapseclient.utils import _find_used
from synapseclient.exceptions import _raise_for_status, SynapseMalformedEntityError, SynapseHTTPError
from synapseclient.dict_object import DictObject

from mock import patch, mock_open, MagicMock
import tempfile
from shutil import rmtree


def setup():
    print('\n')
    print('~' * 60)
    print(os.path.basename(__file__))
    print('~' * 60)

def test_activity_creation_from_dict():
    """test that activities are created correctly from a dictionary"""
    d = {'name':'Project Fuzz',
         'description':'hipster beard dataset',
         'used':[ {'reference':{'targetId':'syn12345', 'versionNumber':42}, 'wasExecuted':True} ]}
    a = Activity(data=d)
    assert a['name'] == 'Project Fuzz'
    assert a['description'] == 'hipster beard dataset'

    usedEntities = a['used']
    assert len(usedEntities) == 1

    u = usedEntities[0]
    assert u['wasExecuted'] == True

    assert u['reference']['targetId'] == 'syn12345'
    assert u['reference']['versionNumber'] == 42


def test_activity_used_execute_methods():
    """test activity creation and used and execute methods"""
    a = Activity(name='Fuzz', description='hipster beard dataset')
    a.used({'id':'syn101', 'versionNumber':42, 'concreteType': 'org.sagebionetworks.repo.model.FileEntity'})
    a.executed('syn102', targetVersion=1)
    usedEntities = a['used']
    len(usedEntities) == 2

    assert a['name'] == 'Fuzz'
    assert a['description'] == 'hipster beard dataset'

    ## ??? are activities supposed to come back in order? Let's not count on it
    used_syn101 = _find_used(a, lambda res: res['reference']['targetId'] == 'syn101')
    assert used_syn101['reference']['targetVersionNumber'] == 42
    assert used_syn101['wasExecuted'] == False

    used_syn102 = _find_used(a, lambda res: res['reference']['targetId'] == 'syn102')
    assert used_syn102['reference']['targetVersionNumber'] == 1
    assert used_syn102['wasExecuted'] == True

def test_activity_creation_by_constructor():
    """test activity creation adding used entities by the constructor"""

    ue1 = {'reference':{'targetId':'syn101', 'targetVersionNumber':42}, 'wasExecuted':False}
    ue2 = {'id':'syn102', 'versionNumber':2, 'concreteType': 'org.sagebionetworks.repo.model.FileEntity'}
    ue3 = 'syn103'

    a = Activity(name='Fuzz', description='hipster beard dataset', used=[ue1, ue3], executed=[ue2])

    # print(a['used'])

    used_syn101 = _find_used(a, lambda res: res['reference']['targetId'] == 'syn101')
    assert used_syn101 is not None
    assert used_syn101['reference']['targetVersionNumber'] == 42
    assert used_syn101['wasExecuted'] == False

    used_syn102 = _find_used(a, lambda res: res['reference']['targetId'] == 'syn102')
    assert used_syn102 is not None
    assert used_syn102['reference']['targetVersionNumber'] == 2
    assert used_syn102['wasExecuted'] == True

    used_syn103 = _find_used(a, lambda res: res['reference']['targetId'] == 'syn103')
    assert used_syn103 is not None

def test_activity_used_url():
    """test activity creation with UsedURLs"""
    u1 = 'http://xkcd.com'
    u2 = {'name':'The Onion', 'url':'http://theonion.com'}
    u3 = {'name':'Seriously advanced code', 'url':'https://github.com/cbare/Pydoku/blob/ef88069f70823808f3462410e941326ae7ffbbe0/solver.py', 'wasExecuted':True}
    u4 = {'name':'Heavy duty algorithm', 'url':'https://github.com/cbare/Pydoku/blob/master/solver.py'}

    a = Activity(name='Foobarbat', description='Apply foo to a bar and a bat', used=[u1, u2, u3], executed=[u3, u4])

    a.executed(url='http://cran.r-project.org/web/packages/glmnet/index.html', name='glm.net')
    a.used(url='http://earthquake.usgs.gov/earthquakes/feed/geojson/2.5/day', name='earthquakes')

    u = _find_used(a, lambda res: 'url' in res and res['url']==u1)
    assert u is not None
    assert u['url'] == u1
    assert u['wasExecuted'] == False

    u = _find_used(a, lambda res: 'name' in res and res['name']=='The Onion')
    assert u is not None
    assert u['url'] == 'http://theonion.com'
    assert u['wasExecuted'] == False

    u = _find_used(a, lambda res: 'name' in res and res['name'] == 'Seriously advanced code')
    assert u is not None
    assert u['url'] == u3['url']
    assert u['wasExecuted'] == u3['wasExecuted']

    u = _find_used(a, lambda res: 'name' in res and res['name'] == 'Heavy duty algorithm')
    assert u is not None
    assert u['url'] == u4['url']
    assert u['wasExecuted'] == True

    u = _find_used(a, lambda res: 'name' in res and res['name'] == 'glm.net')
    assert u is not None
    assert u['url'] == 'http://cran.r-project.org/web/packages/glmnet/index.html'
    assert u['wasExecuted'] == True

    u = _find_used(a, lambda res: 'name' in res and res['name'] == 'earthquakes')
    assert u is not None
    assert u['url'] == 'http://earthquake.usgs.gov/earthquakes/feed/geojson/2.5/day'
    assert u['wasExecuted'] == False


def test_activity_parameter_errors():
    """Test error handling in Activity.used()"""
    a = Activity(name='Foobarbat', description='Apply foo to a bar and a bat')
    assert_raises(SynapseMalformedEntityError, a.used, ['syn12345', 'http://google.com'], url='http://amazon.com')
    assert_raises(SynapseMalformedEntityError, a.used, 'syn12345', url='http://amazon.com')
    assert_raises(SynapseMalformedEntityError, a.used, 'http://amazon.com', targetVersion=1)


def test_is_url():
    """test the ability to determine whether a string is a URL"""
    assert utils.is_url("http://mydomain.com/foo/bar/bat?asdf=1234&qewr=ooo")
    assert utils.is_url("http://xkcd.com/1193/")
    assert not utils.is_url("syn123445")    
    assert not utils.is_url("wasssuuuup???")
    assert utils.is_url('file://foo.com/path/to/file.xyz')
    assert utils.is_url('file:///path/to/file.xyz')
    assert utils.is_url('file:/path/to/file.xyz')
    assert utils.is_url('file:///c:/WINDOWS/clock.avi')
    assert utils.is_url('file:c:/WINDOWS/clock.avi')
    assert not utils.is_url('c:/WINDOWS/ugh/ugh.ugh')

def test_windows_file_urls():
    url = 'file:///c:/WINDOWS/clock.avi'
    assert utils.is_url(url)
    assert utils.file_url_to_path(url, verify_exists=False) == 'c:/WINDOWS/clock.avi', utils.file_url_to_path(url)


def test_is_in_path():
    #Path as returned form syn.restGET('entity/{}/path')
    path = {u'path': [{u'id': u'syn4489',  u'name': u'root', u'type': u'org.sagebionetworks.repo.model.Folder'},
                      {u'id': u'syn537704', u'name': u'my Test project', u'type': u'org.sagebionetworks.repo.model.Project'},
                      {u'id': u'syn2385356',u'name': u'.emacs', u'type': u'org.sagebionetworks.repo.model.FileEntity'}]}

    assert utils.is_in_path('syn537704', path)  
    assert not utils.is_in_path('syn123', path)

def test_id_of():
    assert utils.id_of(1) == '1'
    assert utils.id_of('syn12345') == 'syn12345'
    assert utils.id_of({'foo':1, 'id':123}) == '123'
    assert_raises(ValueError, utils.id_of, {'foo':1, 'idzz':123})
    assert utils.id_of({'properties':{'id':123}}) == '123'
    assert_raises(ValueError, utils.id_of, {'properties':{'qq':123}})
    assert_raises(ValueError, utils.id_of, object())

    class Foo:
        def __init__(self, id_attr_name,id):
            self.properties = {id_attr_name:id}

    id_attr_names = ['id', 'ownerId', 'tableId']

    for attr_name in id_attr_names:
        foo = Foo(attr_name, 123)
        assert utils.id_of(foo) == '123'

def test_guess_file_name():
    assert utils.guess_file_name('a/b') == 'b'
    assert utils.guess_file_name('file:///a/b') == 'b'
    assert utils.guess_file_name('A:/a/b') == 'b'
    assert utils.guess_file_name('B:/a/b/') == 'b'
    assert utils.guess_file_name('c:\\a\\b') == 'b'
    assert utils.guess_file_name('d:\\a\\b\\') == 'b'
    assert utils.guess_file_name('E:\\a/b') == 'b'
    assert utils.guess_file_name('F:\\a/b/') == 'b'
    assert utils.guess_file_name('/a/b') == 'b'
    assert utils.guess_file_name('/a/b/') == 'b'
    assert utils.guess_file_name('http://www.a.com/b') == 'b'
    assert utils.guess_file_name('http://www.a.com/b/') == 'b'
    assert utils.guess_file_name('http://www.a.com/b?foo=bar') == 'b'
    assert utils.guess_file_name('http://www.a.com/b/?foo=bar') == 'b'
    assert utils.guess_file_name('http://www.a.com/b?foo=bar&arga=barga') == 'b'
    assert utils.guess_file_name('http://www.a.com/b/?foo=bar&arga=barga') == 'b'

def test_extract_filename():
    assert utils.extract_filename('attachment; filename="fname.ext"') == "fname.ext"
    assert utils.extract_filename('attachment; filename=fname.ext') == "fname.ext"
    assert utils.extract_filename(None) is None
    assert utils.extract_filename(None, "fname.ext") == "fname.ext"

def test_version_check():
    from synapseclient.version_check import _version_tuple
    assert _version_tuple('0.5.1.dev200', levels=2) == ('0', '5')
    assert _version_tuple('0.5.1.dev200', levels=3) == ('0', '5', '1')
    assert _version_tuple('1.6', levels=3) == ('1', '6', '0')

def test_normalize_path():
    ## tests should pass on reasonable OSes and also on windows

    ## resolves relative paths
    assert len(utils.normalize_path('asdf.txt')) > 8

    ## doesn't resolve home directory references
    #assert '~' not in utils.normalize_path('~/asdf.txt')

    ## converts back slashes to forward slashes
    assert utils.normalize_path('\\windows\\why\\why\\why.txt')

    ## what's the right thing to do for None?
    assert utils.normalize_path(None) is None

def test_limit_and_offset():
    def query_params(uri):
        """Return the query params as a dict"""
        return dict([kvp.split('=') for kvp in uri.split('?')[1].split('&')])

    qp = query_params(utils._limit_and_offset('/asdf/1234', limit=10, offset=0))
    assert qp['limit'] == '10'
    assert qp['offset'] == '0'

    qp = query_params(utils._limit_and_offset('/asdf/1234?limit=5&offset=10', limit=25, offset=50))
    assert qp['limit'] == '25'
    assert qp['offset'] == '50'
    assert len(qp) == 2

    qp = query_params(utils._limit_and_offset('/asdf/1234?foo=bar', limit=10, offset=30))
    assert qp['limit'] == '10'
    assert qp['offset'] == '30'
    assert qp['foo'] == 'bar'
    assert len(qp) == 3

    qp = query_params(utils._limit_and_offset('/asdf/1234?foo=bar&a=b', limit=10))
    assert qp['limit'] == '10'
    assert 'offset' not in qp
    assert qp['foo'] == 'bar'
    assert qp['a'] == 'b'
    assert len(qp) == 3


def test_utils_extract_user_name():
    profile = {'firstName':'Madonna'}
    assert utils.extract_user_name(profile) == 'Madonna'
    profile = {'firstName':'Oscar', 'lastName':'the Grouch'}
    assert utils.extract_user_name(profile) == 'Oscar the Grouch'
    profile['displayName'] = None
    assert utils.extract_user_name(profile) == 'Oscar the Grouch'
    profile['displayName'] = ''
    assert utils.extract_user_name(profile) == 'Oscar the Grouch'
    profile['displayName'] = 'Assistant Professor Oscar the Grouch, PhD'
    assert utils.extract_user_name(profile) == 'Assistant Professor Oscar the Grouch, PhD'
    profile['userName'] = 'otg'
    assert utils.extract_user_name(profile) == 'otg'

def test_is_json():
    assert utils._is_json('application/json')
    assert utils._is_json('application/json;charset=ISO-8859-1')
    assert not utils._is_json('application/flapdoodle;charset=ISO-8859-1')
    assert not utils._is_json(None)
    assert not utils._is_json('')

def test_unicode_output():
    encoding = sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'no encoding'
    print("\nPython thinks your character encoding is:", encoding)
    if encoding and encoding.lower() in ['utf-8', 'utf-16']:
        print("ȧƈƈḗƞŧḗḓ uʍop-ǝpısdn ŧḗẋŧ ƒǿř ŧḗşŧīƞɠ")
    else:
        print("can't display unicode, skipping test_unicode_output...")

def test_normalize_whitespace():
    assert "zip tang pow a = 2" == utils.normalize_whitespace("   zip\ttang   pow   \n    a = 2   ")
    result = utils.normalize_lines("   zip\ttang   pow   \n    a = 2   \n    b = 3   ")
    assert "zip tang pow\na = 2\nb = 3" == result


def test_query_limit_and_offset():
    query, limit, offset = utils.query_limit_and_offset("select foo from bar where zap > 2 limit 123 offset 456")
    print(query, limit, offset)
    assert query == "select foo from bar where zap > 2"
    assert limit == 123
    assert offset == 456

    query, limit, offset = utils.query_limit_and_offset("select limit from offset where limit==2 limit 123 offset 456")
    assert query == "select limit from offset where limit==2"
    assert limit == 123
    assert offset == 456

    query, limit, offset = utils.query_limit_and_offset("select foo from bar where zap > 2 limit 123")
    assert query == "select foo from bar where zap > 2"
    assert limit == 123
    assert offset == 1

    query, limit, offset = utils.query_limit_and_offset("select foo from bar where zap > 2 limit 65535", hard_limit=1000)
    assert query == "select foo from bar where zap > 2"
    assert limit == 1000
    assert offset == 1

def test_as_urls():
    assert utils.as_url("C:\\Users\\Administrator\\AppData\\Local\\Temp\\2\\tmpvixuld.txt") == "file:///C:/Users/Administrator/AppData/Local/Temp/2/tmpvixuld.txt"
    assert utils.as_url("/foo/bar/bat/zoinks.txt") == "file:///foo/bar/bat/zoinks.txt"
    assert utils.as_url("http://foo/bar/bat/zoinks.txt") == "http://foo/bar/bat/zoinks.txt"
    assert utils.as_url("ftp://foo/bar/bat/zoinks.txt") == "ftp://foo/bar/bat/zoinks.txt"
    assert utils.as_url("sftp://foo/bar/bat/zoinks.txt") == "sftp://foo/bar/bat/zoinks.txt"


def test_time_manipulation():
    round_tripped_datetime = utils.datetime_to_iso(
                                utils.from_unix_epoch_time_secs(
                                    utils.to_unix_epoch_time_secs(
                                        utils.iso_to_datetime("2014-12-10T19:09:34.000Z"))))
    print(round_tripped_datetime)
    assert "2014-12-10T19:09:34.000Z" == round_tripped_datetime, round_tripped_datetime

    round_tripped_datetime = utils.datetime_to_iso(
                                utils.from_unix_epoch_time_secs(
                                    utils.to_unix_epoch_time_secs(
                                        utils.iso_to_datetime("1969-04-28T23:48:34.123Z"))))
    print(round_tripped_datetime)
    assert "1969-04-28T23:48:34.123Z" == round_tripped_datetime, round_tripped_datetime

    ## check that rounding to milliseconds works
    round_tripped_datetime = utils.datetime_to_iso(
                                utils.from_unix_epoch_time_secs(
                                    utils.to_unix_epoch_time_secs(
                                        utils.iso_to_datetime("1969-04-28T23:48:34.999499Z"))))
    print(round_tripped_datetime)
    assert "1969-04-28T23:48:34.999Z" == round_tripped_datetime, round_tripped_datetime

    ## check that rounding to milliseconds works
    round_tripped_datetime = utils.datetime_to_iso(
                                utils.from_unix_epoch_time_secs(
                                    utils.to_unix_epoch_time_secs(
                                        utils.iso_to_datetime("1969-04-27T23:59:59.999999Z"))))
    print(round_tripped_datetime)
    assert "1969-04-28T00:00:00.000Z" == round_tripped_datetime, round_tripped_datetime


def test_raise_for_status():
    class FakeResponse(DictObject):
        def json(self):
            return self._json

    response = FakeResponse(
        status_code=501,
        headers={"content-type":"application/json;charset=utf-8"},
        reason="SchlumpError",
        text='{"reason":"it schlumped"}',
        _json={"reason":"it schlumped"},
        request=DictObject(
            url="http://foo.com/bar/bat",
            headers={"xyz":"pdq"},
            method="PUT",
            body="body"))

    assert_raises(SynapseHTTPError, _raise_for_status, response, verbose=False)


def test_treadsafe_generator():
    @utils.threadsafe_generator
    def generate_letters():
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            yield c

    "".join(letter for letter in generate_letters()) == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def test_extract_synapse_id_from_query():
    assert utils._extract_synapse_id_from_query("select * from syn1234567") == "syn1234567"
    assert utils._extract_synapse_id_from_query("select * from syn1234567 where foo = 'bar'") == "syn1234567"
    assert utils._extract_synapse_id_from_query("select * from syn1") == "syn1"
    assert utils._extract_synapse_id_from_query("select foo from syn99999999999") == "syn99999999999"


def test_temp_download_filename():
    temp_destination = utils.temp_download_filename("/foo/bar/bat", 12345)
    assert temp_destination == "/foo/bar/bat.synapse_download_12345", temp_destination

    regex = r'/foo/bar/bat.synapse_download_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    assert re.match(regex, utils.temp_download_filename("/foo/bar/bat", None))


@patch('zipfile.ZipFile')
@patch('os.makedirs')
@patch('os.path.exists', return_value = False)
def test_extract_zip_file_to_directory(mocked_path_exists, mocked_makedir, mocked_zipfile):
    file_base_name = 'test.txt'
    file_dir = 'some/folders/'
    target_dir = tempfile.mkdtemp() #TODO rename
    expected_filepath = os.path.join(target_dir, file_base_name)

    try:
        #call the method and make sure correct values are being used
        with patch('synapseclient.utils.open', mock_open(), create=True) as mocked_open:
            actual_filepath = utils._extract_zip_file_to_directory(mocked_zipfile, file_dir + file_base_name, target_dir)

            #make sure it returns the correct cache path
            assert_equal(expected_filepath, actual_filepath)

            #make sure it created the cache folders
            mocked_makedir.assert_called_once_with(target_dir)

            #make sure zip was read and file was witten
            mocked_open.assert_called_once_with(expected_filepath, 'wb')
            mocked_zipfile.read.assert_called_once_with(file_dir + file_base_name)
            mocked_open().write.assert_called_once_with(mocked_zipfile.read())
    finally:
        rmtree(target_dir, ignore_errors=True)

def _calling_module_test_helper():
    return utils.caller_module_name(inspect.currentframe())

def test_calling_module():
    # 'case' is the name of the module with which nosetests runs these tests
    # 'unit_test' is the name of the module in which this test resides
    # we made a helper so that the call order is: case.some_function_for_running_tests() -> unit_test.test_calling_module() -> unit_test._calling_module_test_helper()
    # since both _calling_module_test_helper and test_calling_module are a part of the unit_test module, we can test that callers of the same module do indeed are skipped
    assert_equal("case", _calling_module_test_helper())

def _helper_test_extract_zip_file_to_directory(zip_entry_name, target_dir, expected_path, ignore_heirarchy):
    fake_data = "Omae Wa Mou Shindeiru. Nani?!"
    mocked_zip_file_obj = MagicMock();
    mocked_zip_file_obj.read = MagicMock(return_value=fake_data);


    with patch.object(utils, "open", mock_open(), create=True) as mocked_open, \
         patch.object(os.path, "exists", return_value=True) as mocked_path_exists:
        final_path = utils._extract_zip_file_to_directory(mocked_zip_file_obj, zip_entry_name, target_dir, ignore_heirarchy)

        assert_equal(expected_path, final_path)

        mocked_path_exists.assert_called_once()
        mocked_open.assert_called_once_with(expected_path, 'wb')
        mocked_open().write.assert_called_once_with(fake_data)

def test_extract_zip_file_to_directory__preserve_heirarchy_is_True():
    zip_entry_name =  "folder/heiarchy/and/then/filename.txt"
    target_dir = "/some/path"

    expected_path = os.path.join(target_dir, zip_entry_name)
    _helper_test_extract_zip_file_to_directory(zip_entry_name, target_dir, expected_path, ignore_heirarchy=False)

def test_extract_zip_file_to_directory__preserve_heirarchy_is_False():
    zip_entry_name =  "folder/heiarchy/and/then/filename.txt"
    target_dir = "/some/path"

    expected_path = os.path.join(target_dir, os.path.basename(zip_entry_name))
    _helper_test_extract_zip_file_to_directory(zip_entry_name, target_dir, expected_path, ignore_heirarchy=True)