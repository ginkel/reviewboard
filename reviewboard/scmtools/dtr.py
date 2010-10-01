import re
import subprocess
import string
from reviewboard.scmtools.dtrclient.dtr import DtrBaseClient 

from django.utils.translation import ugettext as _

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool, ChangeSet, \
                                      HEAD, PRE_CREATION
from reviewboard.scmtools.errors import SCMError, EmptyChangeSetError


class EmptyChangesetError(SCMError):
    def __init__(self, changenum):
        SCMError.__init__(self, _('Changeset %s is empty') % changenum)


class DtrClient(DtrBaseClient):
    def __init__(self, server, user, password):
        DtrBaseClient.__init__(self, server, user, password)


class DtrTool(SCMTool):
    def __init__(self, repository):
        SCMTool.__init__(self, repository)

        self.host = str(repository.mirror_path or repository.path)
        self.user = str(repository.username)
        self.password = str(repository.password)

        # We defer actually connecting until just before we do some operation
        # that requires an active connection to the perforce depot.  This
        # connection is then left open as long as possible.
        self.client = DtrClient(self.host, self.user, self.password)

        self.uses_atomic_revisions = True

    def get_changeset(self, changesetid):
        activity = self.client.dtr_get_activity(changesetid)
        if activity:
            return self.parse_activity(activity, changesetid)
        return None

    def get_diffs_use_absolute_paths(self):
        return True

    def get_file(self, path, revision=HEAD):
		if path.startswith("/dtr"):
			fixedpath = path
		else:
			fixedpath = ("/dtr%s" % path)
		try:
			idx = string.index(fixedpath, '#')
			fixedpath = fixedpath[:idx]
		except ValueError:
			pass

		#raise Exception(fixedpath)

		resp = self.client._dtr_request("GET", fixedpath)
		return resp.read()

    def parse_diff_revision(self, file_str, revision_str):
        filename, revision = revision_str.rsplit('#', 1)
        return filename, revision

    def get_filenames_in_revision(self, revision):
        return self.get_changeset(revision).files

    @staticmethod
    def parse_activity(act, changenum):
        if not act:
            return None

        changeset = ChangeSet()
        changeset.changenum = changenum

        # At it's most basic, a perforce changeset description has three
        # sections.
        #
        # ---------------------------------------------------------
        # Change <num> by <user>@<client> on <timestamp> *pending*
        #
        #         description...
        #         this can be any number of lines
        #
        # Affected files ...
        #
        # //depot/branch/etc/file.cc#<revision> branch
        # //depot/branch/etc/file.hh#<revision> delete
        # ---------------------------------------------------------
        #
        # At the moment, we only care about the description and the list of
        # files.  We take the first line of the description as the summary.
        #
        # We parse the username out of the first line to check that one user
        # isn't attempting to "claim" another's changelist.  We then split
        # everything around the 'Affected files ...' line, and process the
        # results.
        changeset.username = act.originator
        changeset.description = act.displayname

        try:
            changeset.files = changedesc['depotFile']
        except KeyError:
            raise EmptyChangesetError(changenum)

        changeset.summary = "%s (%s) submitted by %s" % (changeset.description, changenum, act.changeset.username)

        return changeset

    def get_fields(self):
        return ['changenum', 'diff_path']

    def get_parser(self, data):
        return DtrDiffParser(data)


class DtrDiffParser(DiffParser):
    SPECIAL_REGEX = re.compile("^==== ([^#]+)#(\d+) ==([AMD])== (.*) ====$")

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_diff_header(self, linenum, info):
        m = self.SPECIAL_REGEX.match(self.lines[linenum])
        if m:
            info['origFile'] = m.group(1)
            info['origInfo'] = "%s#%s" % (m.group(1), m.group(2))
            info['newFile'] = m.group(4)
            info['newInfo'] = ""
            linenum += 1

            if linenum < len(self.lines) and \
               (self.lines[linenum].startswith("Binary files ") or
                self.lines[linenum].startswith("Files ")):
                info['binary'] = True
                linenum += 1

            # In this case, this *is* our diff header. We don't want to
            # let the next line's real diff header be a part of this one,
            # so return early and don't invoke the next.
            return linenum

        return super(DtrDiffParser, self).parse_diff_header(linenum, info)
