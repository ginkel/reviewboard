'''
Created on May 5, 2009

@author: D044539
'''

import base64
import datetime
import urllib
import urllib2
import httplib
import string
import xml.sax
import xml.sax.handler

class DtrBaseObject(object):
    def __init__(self):
        object.__init__(self)

    def __repr__(self):
        return self.__str__()


class DtrWorkspace(DtrBaseObject):
    def __init__(self, path, history):
        self.path = path
        self.history = history

    def __str__(self):
        return "DtrWorkspace[path=%s, history=%s]" % (self.path, self.history)

    def get_path(self):
        return self.path
    
    def get_history(self):
        return self.history

        
class DtrActivity(DtrBaseObject):
    VERSIONSET_UNKNOWN = 0
    VERSIONSET_OPEN = 1
    VERSIONSET_CLOSED = 2
    
    def __init__(self, name, displayname, version_set_state, client_id, originator):
        DtrBaseObject.__init__(self)

        self.name = name
        self.displayname = displayname
        self.integrations = []
        self.version_set = []
        self.content_set = []
        self.workspace_name = None
        self.workspace = None
        self.originator = originator
        
        if version_set_state == "open":
            self.version_set_state = self.VERSIONSET_OPEN
        elif version_set_state == "closed":
            self.version_set_state = self.VERSIONSET_CLOSED
        else:
            self.version_set_state = self.VERSIONSET_UNKNOWN
        
        if not client_id is None:
            split_client = string.rsplit(client_id, ":", 1)
            self.client_hostname = split_client[1]
            self.client_path = split_client[0]
        else:
            self.client_hostname = None
            self.client_path = None

    def __str__(self):
        return "DtrActivity[name=%s, displayname=%s, integrations=%s, versionset=%s, contentset=%s, versionset_state=%s, client_host=%s, client_path=%s, workspace=%s]" % (self.name, self.displayname, self.integrations, self.version_set, self.content_set, self.version_set_state, self.client_hostname, self.client_path, self.workspace)
        
    def _add_integration(self, integration):
        self.integrations.append(integration)

    def _add_version(self, version):
        self.version_set.append(version)

    def _add_content(self, resource):
        self.content_set.append(resource)
        
    def get_name(self):
        return self.name
    
    def get_display_name(self):
        return self.displayname
    
    def get_integrations(self):
        return self.integrations

    def get_oldest_integration(self):
        result = None
        oldest_date = None
        
        for integration in self.integrations:
            if oldest_date is None or integration.get_creation_date() < oldest_date:
                result = integration
                oldest_date = integration.get_creation_date()
        
        return result
    
    def get_version_set(self):
        return self.version_set

    def get_version_set_state(self):
        return self.version_set_state

    def get_content_set(self):
        return self.content_set

    def get_client_hostname(self):
        return self.client_hostname
    
    def get_client_path(self):
        return self.client_path

    def get_workspace(self):
        return self.workspace

        
class DtrIntegration(DtrBaseObject):
    def __init__(self, path, workspace, creationdate, isn):
        DtrBaseObject.__init__(self)
        self.path = path
        self.workspace = workspace
        self.creationdate = creationdate
        self.isn = isn

    def __str__(self):
        return "DtrIntegration[path=%s, ws=%s, creation=%s, isn=%s]" % (self.path, self.workspace, self.creationdate, self.isn)

    def __repr__(self):
        return self.__str__()

    def get_path(self):
        return self.path
    
    def get_workspace(self):
        return self.workspace
    
    def get_creation_date(self):
        return self.creationdate
    
    def get_isn(self):
        return self.isn


class DtrFile(DtrBaseObject):
    def __init__(self, name, path):
        DtrBaseObject.__init__(self)
        self.name = name
        self.path = path

    def __str__(self):
        return "DtrFile[name=%s, path=%s]" % (self.name, self.path)

    def get_name(self):
        return self.name
    
    def get_path(self):
        return self.path
    
    def get_revision(self):
        return 1
    
    def is_created(self):
        return True
    
    def is_deleted(self):
        return False


class DtrBaseVersionedResource(DtrFile):
    def __init__(self, name, path, revision, deleted):
        DtrFile.__init__(self, name, path)
        self.deleted = deleted
        self.revision = revision

    def get_revision(self):
        return self.revision
    
    def is_created(self):
        return self.revision == 0
    
    def is_deleted(self):
        return self.deleted
    

class DtrVersion(DtrBaseVersionedResource):
    def __init__(self, name, path, revision, deleted):
        DtrBaseVersionedResource.__init__(self, name, path, revision, deleted)

    def __str__(self):
        return "DtrVersion[name=%s, path=%s, rev=%s, created=%s, deleted=%s]" % (self.name, self.path, self.revision, self.is_created(), self.deleted)


class DtrWorkingResource(DtrBaseVersionedResource):
    def __init__(self, name, path, revision, deleted, base_version):
        DtrBaseVersionedResource.__init__(self, name, path, revision, deleted)
        self.base_version = base_version

    def __str__(self):
        return "DtrWorkingResource[name=%s, path=%s, rev=%s, created=%s, deleted=%s, base_version=%s]" % (self.name, self.path, self.revision, self.is_created(), self.deleted, self.base_version)

    def get_base_version(self):
        return self.base_version


class DtrBaseClient(object):
    def __init__(self):
        self.conn = None
        self.server = DTR_SERVER
        self.user = "anzeiger"
        self.password = "display"

    def __init__(self, server, user, password):
        self.conn = None
        self.server = server
        self.user = user
        self.password = password

    def __del__(self):
        if self.conn != None:
            self.conn.close()

    def _connect(self):
        if self.conn == None:
            #self.conn = httplib.HTTPConnection(self.get_repository_info().path)
            self.conn = httplib.HTTPConnection(self.server)
    
    class DtrBaseHandler(xml.sax.handler.ContentHandler, object):
        STATE_INIT = 0
        STATE_UNKNOWN_ELEM = 255

        def __init__(self):
            self.state = self.STATE_INIT
            self.old_state = - 1
            self.unknown_level = 0
            self.buffer = ""

        def characters(self, data):
            self.buffer += data
        

    class DtrActivityHandler(DtrBaseHandler):
        STATE_DN = 1
        STATE_IS = 2
        STATE_IS_HREF = 3
        STATE_VS = 4
        STATE_VS_HREF = 5
        STATE_VSS = 6
        STATE_CLIENT_ID = 7
        STATE_CS = 8
        STATE_CS_HREF = 9
        STATE_WORKSPACE = 10
        STATE_WORKSPACE_HREF = 11
        STATE_ORIGINATOR = 12

        def __init__(self):
            super(self.__class__, self).__init__()
            self.integrations = []
            self.version_set = []
            self.version_set_state = None
            self.content_set = []
            self.client_id = None
            self.displayname = None
            self.workspace = None
            self.originator = None
            
        def startElement(self, name, attributes):
            if self.state == self.STATE_INIT:
                if name == "DAV:displayname":
                    self.state = self.STATE_DN
                elif name == "DAV:workspace":
                    self.state = self.STATE_WORKSPACE
                elif name == "x:integration-set":
                    self.state = self.STATE_IS
                elif name == "x:activity-content-set":
                    self.state = self.STATE_CS
                elif name == "x:version-set":
                    self.state = self.STATE_VS
                elif name == "x:version-set-state":
                    self.state = self.STATE_VSS
                elif name == "x:originator":
                    self.state = self.STATE_ORIGINATOR
                elif name == "XCM_CLIENT:client-id":
                    self.state = self.STATE_CLIENT_ID
                elif not (name == "DAV:multistatus" or name == "DAV:response" or name == "DAV:propstat" or name == "DAV:prop"):
                    self.old_state = self.state
                    self.state = self.STATE_UNKNOWN_ELEM
                    self.unknown_level += 1
            elif self.state == self.STATE_WORKSPACE and name == "DAV:href":
                self.state = self.STATE_WORKSPACE_HREF
            elif self.state == self.STATE_IS and name == "DAV:href":
                self.state = self.STATE_IS_HREF
            elif self.state == self.STATE_VS and name == "DAV:href":
                self.state = self.STATE_VS_HREF
            elif self.state == self.STATE_CS and name == "DAV:href":
                self.state = self.STATE_CS_HREF
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level += 1
            else:
                self.old_state = self.state
                self.state = self.STATE_UNKNOWN_ELEM
                self.unknown_level += 1
        
        def endElement(self, name):
            if self.state == self.STATE_IS_HREF and name == "DAV:href":
                self.integrations.append(self.buffer)
                self.state = self.STATE_IS
            elif self.state == self.STATE_VS_HREF and name == "DAV:href":
                self.version_set.append(self.buffer)
                self.state = self.STATE_VS
            elif self.state == self.STATE_CS_HREF and name == "DAV:href":
                self.content_set.append(self.buffer)
                self.state = self.STATE_CS
            elif self.state == self.STATE_WORKSPACE_HREF and name == "DAV:href":
                self.workspace = self.buffer
                self.state = self.STATE_WORKSPACE
            elif self.state == self.STATE_CS and name == "x:activity-content-set":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_IS and name == "x:integration-set":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_VS and name == "x:version-set":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_ORIGINATOR and name == "x:originator":
                self.originator = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_DN and name == "DAV:displayname":
                self.displayname = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_WORKSPACE and name == "DAV:workspace":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_VSS and name == "x:version-set-state":
                self.version_set_state = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_CLIENT_ID and name == "XCM_CLIENT:client-id":
                self.client_id = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level -= 1
                if self.unknown_level == 0:
                    self.state = self.old_state
                    self.old_state = - 1
        
            self.buffer = ""


    class DtrIntegrationHandler(DtrBaseHandler):
        STATE_WORKSPACE = 1
        STATE_WORKSPACE_HREF = 2
        STATE_CREATIONDATE = 3
        STATE_ISN = 4
       
        def __init__(self):
            super(self.__class__, self).__init__()
            self.workspace = None
            self.isn = - 1
            self.creationdate = None
            
        def startElement(self, name, attributes):
            if self.state == self.STATE_INIT:
                if name == "DAV:workspace":
                    self.state = self.STATE_WORKSPACE
                elif name == "DAV:creationdate":
                    self.state = self.STATE_CREATIONDATE
                elif name == "x:isn":
                    self.state = self.STATE_ISN
                elif not (name == "DAV:multistatus" or name == "DAV:response" or name == "DAV:propstat" or name == "DAV:prop"):
                    self.old_state = self.state
                    self.state = self.STATE_UNKNOWN_ELEM
                    self.unknown_level += 1
            elif self.state == self.STATE_WORKSPACE and name == "DAV:href":
                self.state = self.STATE_WORKSPACE_HREF
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level += 1
            else:
                self.old_state = self.state
                self.state = self.STATE_UNKNOWN_ELEM
                self.unknown_level += 1
            
        def endElement(self, name):
            if self.state == self.STATE_WORKSPACE and name == "DAV:workspace":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_WORKSPACE_HREF and name == "DAV:href":
                self.workspace = self.buffer
                self.state = self.STATE_WORKSPACE
            elif self.state == self.STATE_CREATIONDATE and name == "DAV:creationdate":
                if len(self.buffer) > 0:
                    self.creationdate = datetime.datetime.strptime(self.buffer, "%Y-%m-%dT%H:%M:%SZ")
                self.state = self.STATE_INIT
            elif self.state == self.STATE_ISN and name == "x:isn":
                self.isn = int(self.buffer)
                # print "Got ISN: %s" % self.isn
                self.state = self.STATE_INIT
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level -= 1
                if self.unknown_level == 0:
                    self.state = self.old_state
                    self.old_state = - 1
                
            self.buffer = ""


    class DtrFileVersionWorkingResourceHandler(DtrBaseHandler):
        STATE_DN = 1
        STATE_SN = 2
        STATE_PATH = 3
        STATE_DELETED = 4
        STATE_BASE_VERSION = 5
        STATE_BASE_VERSION_HREF = 6
        STATE_RES_TYPE = 7
        
        def __init__(self):
            super(self.__class__, self).__init__()
            self.name = None
            self.revision = - 1
            self.path = None
            self.deleted = False
            self.base_version = None
            self.resource_type = None
            self.workspace = None
            
        def startElement(self, name, attributes):
            if self.state == self.STATE_INIT:
                if name == "DAV:displayname":
                    self.state = self.STATE_DN
                elif name == "x:sequence-number":
                    self.state = self.STATE_SN
                elif name == "x:path":
                    self.state = self.STATE_PATH
                elif name == "x:deleted":
                    self.state = self.STATE_DELETED
                elif name == "x:base-version":
                    self.state = self.STATE_BASE_VERSION
                elif name == "x:resource-type":
                    self.state = self.STATE_RES_TYPE
                elif not (name == "DAV:multistatus" or name == "DAV:response" or name == "DAV:propstat" or name == "DAV:prop"):
                    self.old_state = self.state
                    self.state = self.STATE_UNKNOWN_ELEM
                    self.unknown_level += 1
            elif self.state == self.STATE_BASE_VERSION and name == "DAV:href":
                self.state = self.STATE_BASE_VERSION_HREF
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level += 1
            else:
                self.old_state = self.state
                self.state = self.STATE_UNKNOWN_ELEM
                self.unknown_level += 1

        def endElement(self, name):
            #if not self.state == self.STATE_UNKNOWN_ELEM:
            #    print name
            
            if self.state == self.STATE_DN and name == "DAV:displayname":
                self.name = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_SN and name == "x:sequence-number":
                self.revision = int(self.buffer)
                self.state = self.STATE_INIT
            elif self.state == self.STATE_PATH and name == "x:path":
                self.path = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_DELETED and name == "x:deleted":
                self.deleted = self.buffer == "T"
                self.state = self.STATE_INIT
            elif self.state == self.STATE_BASE_VERSION and name == "x:base-version":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_BASE_VERSION_HREF and name == "DAV:href":
                self.base_version = self.buffer
                self.state = self.STATE_BASE_VERSION
            elif self.state == self.STATE_RES_TYPE and name == "x:resource-type":
                self.resource_type = string.lower(self.buffer)
                self.state = self.STATE_INIT
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level -= 1
                if self.unknown_level == 0:
                    self.state = self.old_state
                    self.old_state = - 1
            
            self.buffer = ""


    class DtrWorkspaceHandler(DtrBaseHandler):
        STATE_WSH = 1
        STATE_WSH_HREF = 2
        STATE_PATH = 3
       
        def __init__(self):
            super(self.__class__, self).__init__()
            self.history = None
            self.path = None
            
        def startElement(self, name, attributes):
            if self.state == self.STATE_INIT:
                if name == "x:path":
                    self.state = self.STATE_PATH
                elif name == "x:workspace-history":
                    self.state = self.STATE_WSH
                elif not (name == "DAV:multistatus" or name == "DAV:response" or name == "DAV:propstat" or name == "DAV:prop"):
                    self.old_state = self.state
                    self.state = self.STATE_UNKNOWN_ELEM
                    self.unknown_level += 1
            elif self.state == self.STATE_WSH and name == "DAV:href":
                self.state = self.STATE_WSH_HREF
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level += 1
            else:
                self.old_state = self.state
                self.state = self.STATE_UNKNOWN_ELEM
                self.unknown_level += 1
            
        def endElement(self, name):
            if self.state == self.STATE_PATH and name == "x:path":
                self.path = self.buffer
                self.state = self.STATE_INIT
            elif self.state == self.STATE_WSH_HREF and name == "DAV:href":
                self.history = self.buffer
                self.state = self.STATE_WSH
            elif self.state == self.STATE_WSH and name == "x:workspace-history":
                self.state = self.STATE_INIT
            elif self.state == self.STATE_UNKNOWN_ELEM:
                self.unknown_level -= 1
                if self.unknown_level == 0:
                    self.state = self.old_state
                    self.old_state = - 1
                
            self.buffer = ""


    def _dtr_request(self, method, path):
        # "Basic" authentication encodes userid:password in base64. Note
        # that base64.encodestring adds some extra newlines/carriage-returns
        # to the end of the result. string.strip is a simple way to remove
        # these characters.
        auth = 'Basic ' + string.strip(base64.encodestring(self.user + ':' + self.password))

        self._connect()

        # get activity details
        self.conn.putrequest(method, path, False, True)
        self.conn.putheader("Authorization", auth)
        self.conn.putheader("Depth", "0")
        self.conn.endheaders()
        self.conn.send("")
        return self.conn.getresponse()

    def _dtr_get_integration(self, integration):
        resp = self._dtr_request("PROPFIND", integration)
        handler = self.DtrIntegrationHandler()
        xml.sax.parseString(resp.read(), handler)
        #if handler.creationdate is None or handler.creationdate == "":
        #    print xmlstr
        return DtrIntegration(integration, handler.workspace, handler.creationdate, handler.isn)
    
    def dtr_get_activity(self, activity):
        resp = self._dtr_request("PROPFIND", activity)
        handler = self.DtrActivityHandler()
        xmldata = resp.read()
        # print xmldata
        xml.sax.parseString(xmldata, handler)

        act = DtrActivity(activity, handler.displayname, handler.version_set_state, handler.client_id, handler.originator)
    
        print "Integrations: %s" % handler.integrations
        for integration in handler.integrations:
            print "Fetching integration: %s" % integration
            act._add_integration(self._dtr_get_integration(integration))

        print "Versions: %s" % handler.version_set
        for version in handler.version_set:
            print "Fetching version: %s" % version
            act._add_version(self._dtr_get_resource(version))

        print "Content Set: %s" % handler.content_set
        for resource in handler.content_set:
            print "Fetching resource: %s" % resource
            act._add_content(self._dtr_get_resource(resource))

        if act.integrations:
            act.workspace_name = act.get_oldest_integration().workspace
        else:
            act.workspace_name = handler.workspace

        print "Fetching workspace details: %s" % act.workspace_name
        act.workspace = self._dtr_get_workspace(act.workspace_name)
        
        return act

    def _dtr_get_resource(self, resource):
        resp = self._dtr_request("PROPFIND", resource)
        handler = self.DtrFileVersionWorkingResourceHandler()
        xmldata = resp.read()
        xml.sax.parseString(xmldata, handler)

        if handler.resource_type == "version":
            return DtrVersion(handler.name, handler.path, handler.revision, handler.deleted)
        elif handler.resource_type == "working_resource":
            #print xmldata
            return DtrWorkingResource(handler.name, handler.path, handler.revision, handler.deleted, handler.base_version)
        elif handler.resource_type == "file":
            return DtrFile(handler.name, handler.path)
        else:
            print xmldata
            raise Exception("Unknown resource type: %s" % handler.resource_type)

    def _dtr_get_workspace(self, workspace):
        resp = self._dtr_request("PROPFIND", workspace)
        handler = self.DtrWorkspaceHandler()
        xmldata = resp.read()
        xml.sax.parseString(xmldata, handler)
        return DtrWorkspace(handler.path, handler.history)

    def _dtr_get_file(self, activity, resource):
        if type(resource) == DtrVersion:
            isn = activity.get_oldest_integration().get_isn()
            if predecessor:
                isn = isn - 1
            resp = self._dtr_request("GET", "%s/byintegration/all/%s%s" % (activity.get_workspace().get_history(), isn, resource.get_path()))
            data = resp.read()
        else:
            if predecessor:
                # predecessor is stored in DTR for open activities
                resp = self._dtr_request("GET", resource.get_base_version())
                data = resp.read()
            else:
                # most recent version is stored locally
                i = open("%s/%s" % (activity.get_client_path(), resource.get_path()), "r")
                data = i.read()
                i.close()

        f = open(tmpfile, "w")
        f.write(self._convert_line_ending(data))
        f.close()

    def _dtr_get_file(self, activity, resource, tmpfile, predecessor):
        if type(resource) == DtrVersion:
            isn = activity.get_oldest_integration().get_isn()
            if predecessor:
                isn = isn - 1
            resp = self._dtr_request("GET", "%s/byintegration/all/%s%s" % (activity.get_workspace().get_history(), isn, resource.get_path()))
            data = resp.read()
        else:
            if predecessor:
                # predecessor is stored in DTR for open activities
                resp = self._dtr_request("GET", resource.get_base_version())
                data = resp.read()
            else:
                # most recent version is stored locally
                i = open("%s/%s" % (activity.get_client_path(), resource.get_path()), "r")
                data = i.read()
                i.close()

        f = open(tmpfile, "w")
        f.write(self._convert_line_ending(data))
        f.close()

    def _convert_line_ending(self, data):
        result = ""
        
        for line in string.split(data, "\n"):
            result = result + line.rstrip("\r\n") + "\n"

        return result
