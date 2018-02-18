from .abstractconnectedshell import AbstractConnectedShell
from .streamreader import PrefixedStreamReader
from .shellresult import ShellResult
from .localshell import LocalShell
from .loggerthread import LoggerThread
from subprocess import Popen, PIPE


class AdbShell(AbstractConnectedShell):

    def __init__(self, hostname, port=5555, *args, **kwargs):
        super(AdbShell, self).__init__(hostname, *args, **kwargs)
        self._hostname = hostname        
        self._port = port
        self._localshell = LocalShell(check_err=True, check_xc=True)
        self.connect()

    def do_connect(self):
        result = self._localshell("adb connect %s:%d" % (self._hostname, self._port), check_err=True, check_xc=True)
        if str(result).find("unable to connect") != -1:
            # for some reason the exit code of 'adb connect' is zero even if the connection cannot be established
            raise RuntimeError(str(result))
        self._connected = True

    def disconnect(self):
        self._localshell("adb disconnect %s:%s" % (self._hostname, self._port), check_err=True)
            
    def execute_command(self, cmd, env):
        self.log_stdin(cmd)
        formatted_command = PrefixedStreamReader.wrap_command(cmd, env)
        adb_command = "adb -s %s:%d shell '%s'" % (self._hostname, self._port, formatted_command.replace('\'', '\'"\'"\''))
        process = Popen(adb_command, env=None, shell=True, stdout=PIPE, stderr=PIPE)

        out, err = [], []
        xc = None
        while True:
            line = process.stdout.readline().rstrip()
            if line == '':
                break
            prefix, line = line[:4], line[4:]
            if prefix == "ERR-":
                self.log_stderr(line)
                err.append(line)
            elif prefix == "OUT-":
                self.log_stdout(line)
                out.append(line)
            elif prefix == "XC--":
                xc = int(line)
        process.wait()
        return ShellResult(cmd, out, err, xc)

    def push(self, local_path, remote_path):
        self.log_oob("pushing '%s' -> '%s'..." % (local_path, remote_path))
        self._localshell("adb push '%s' '%s'" % (local_path, remote_path))
        self.log_oob("done!")

    def pull(self, local_path, remote_path):
        self.log_oob("pulling '%s' <- '%s'..." % (local_path, remote_path))
        self._localshell("adb pull '%s' '%s'" % (remote_path, local_path))
        self.log_oob("done!")


