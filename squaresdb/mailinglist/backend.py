from pathlib import Path
import subprocess

# This is based on a version from the ASA DB
# https://github.com/dehnert/asa-db/blob/master/asadb/util/mailinglist.py
# Commit 356174b3d3fd8f7aeeb346af06822b9033439c06
# MoiraList requires the `mit` module, which provides kinit
#import mit
mit = None # pylint:disable=invalid-name

# Directory containing membership/, gate/, etc.
BASE_DIR = Path(__file__).resolve().parent.parent

class MailingList:
    def __init__(self, name, ):
        self.name = name

    def list_members(self, ):
        raise NotImplementedError

    def change_members(self, add_members, delete_members, ):
        raise NotImplementedError


BLANCHE_PATH="/usr/bin/blanche"
class MoiraList(MailingList):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ccache = None

    @property
    def ccache(self, ):
        if not self._ccache:
            self._ccache = mit.kinit()
        return self._ccache

    def list_members(self, ):
        # pylint:disable=unreachable
        raise NotImplementedError
        with subprocess.Popen([BLANCHE_PATH, self.name, ],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as res:
            stdout, stderr = res.communicate()
            if res.returncode:
                raise RuntimeError("Failed to list members: %s" % (stderr, ))
        members = stdout.strip().split("\n")
        return members

    def strip_mit(self, email):
        if '@' in email:
            local, domain = email.split('@')
            if domain.lower() == 'mit.edu':
                return local
        return email

    def canonicalize_member(self, member):
        if isinstance(member, tuple):
            name, email = member
        else:
            name = None
            email = member
        email = self.strip_mit(email)
        return name, email

    def change_members(self, add_members, delete_members, ):
        """
        Add and/or remove members from the list.
        """

        # Note that it passes all members on the commandline, so it shouldn't be
        # used for large lists at the moment. OTOH, "large" appears to be
        # 2M characters, so.
        # If that becomes an issue, it should probably check the number of
        # changes, and use -al / -dl with a tempfile as appropriate.

        env = dict(KRB5CCNAME=self.ccache.name)
        cmdline = [BLANCHE_PATH, self.name, ]

        for member in add_members:
            name, email = self.canonicalize_member(member)
            if name:
                cmdline.extend(('-at', email, name))
            else:
                cmdline.extend(('-a', email))

        for member in delete_members:
            name, email = self.canonicalize_member(member)
            cmdline.extend(('-d', email))

        with subprocess.Popen(cmdline,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              env=env, ) as res:
            stdout, _stderr = res.communicate()
        return stdout



MMBLANCHE_PATH = Path(__file__).resolve().parent / "mmblanche"
class MailmanList(MailingList):
    def list_members(self, ):
        with subprocess.Popen([MMBLANCHE_PATH, self.name, ], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as res:
            stdout, stderr = res.communicate()
            if res.returncode:
                raise RuntimeError("Failed to list members: %s" % (stderr, ))
        members = stdout.strip().split("\n")
        return members

    def change_members(self, add_members, delete_members, ):
        """
        Add and/or remove members from the list.
        """

        # Note that it passes all members on the commandline, so it shouldn't be
        # used for large lists at the moment. OTOH, "large" appears to be
        # 2M characters, so.
        # If that becomes an issue, it should probably check the number of
        # changes, and use -al / -dl with a tempfile as appropriate.

        cmdline = [MMBLANCHE_PATH, self.name, ]
        for member in add_members:
            cmdline.append('-a')
            if isinstance(member, tuple):
                name, email = member
                name = name.replace('"', "''")
                member = '"%s" <%s>' % (name, email, )
            cmdline.append(member)
        for member in delete_members:
            cmdline.append('-d')
            if isinstance(member, tuple):
                name, member = member
            cmdline.append(member)
        with subprocess.Popen(cmdline,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as res:
            stdout, stderr = res.communicate()
        assert stderr=="", ("stderr unexpectedly non-empty: %s" % (stderr, ))
        return stdout
