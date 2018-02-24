from paramiko import SSHClient, AutoAddPolicy

from .abstractshell import AbstractShell
from .abstractconnectedshell import AbstractConnectedShell
from .shellresult import IterableShellResult
from .queue import Queue
from .streamreader import StandardStreamReader
from threading import Thread


class SecureShell(AbstractConnectedShell):

    def __init__(self, hostname, username, password=None, port=22, **kwargs):        
        super(SecureShell, self).__init__(hostname, **kwargs)
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self.connect()

    def do_connect(self):
        self._client = SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(AutoAddPolicy())
        self._client.connect(hostname=self._hostname, port=self._port, username=self._username, password=self._password)

    def do_disconnect(self):
        self._client.close()

    def execute_command(self, command, env, wait, check_err):
        for var, val in env.items():
            command = "%s=%s; " % (var, val) + command
        chan = self._client.get_transport().open_session()
        chan.exec_command(command)
        queue = Queue()
        StandardStreamReader(chan.makefile("r"), 1, queue)
        StandardStreamReader(chan.makefile_stderr("r"), 2, queue)
        def post_process_exit_code():
            queue.put( (0, chan.recv_exit_status()) )
            queue.put( (0, None) )
        Thread(target=post_process_exit_code).start()
        return IterableShellResult(command, queue, wait, check_err)

