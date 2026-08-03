import os
import paramiko
import logging
from stat import S_ISDIR, S_ISREG
import tempfile
from .fileReader import FileReader
import pandas as pd
from io import StringIO
import yaml


class SshClient(FileReader):
    """
    SSH-based file reader that extends FileReader to handle file operations over SSH/SFTP.
    Enables reading, writing, listing, and transferring files on a remote server securely.
    """

    def __init__(self, server="alma.icr.ac.uk", username=None, password=None, sftp="alma-app.icr.ac.uk", port=22,
                 key_filename=None, passphrase=None):
        """
        Initialize SSH and SFTP connection parameters.

        :param server: Main SSH server address.
        :type server: str
        :param username: SSH username.
        :type username: str
        :param password: SSH password.
        :type password: str
        :param sftp: SFTP host (defaults to `server` if not specified).
        :type sftp: str
        :param key_filename: Explicit private key path(s) to authenticate with. If not
            given, falls back to the IdentityFile(s) declared for this host in
            ``~/.ssh/config`` (Paramiko does not read that file on its own), then to
            Paramiko's normal ssh-agent/default-key discovery.
        :type key_filename: str | list[str] | None
        :param passphrase: Passphrase for an encrypted private key, if needed.
        :type passphrase: str | None
        """
        super().__init__()
        self.remote = True
        self.server = server.strip()
        self.sftp = self.server if sftp is None else sftp.strip()
        self.username = username.strip() if username else None
        self.password = password.strip() if password else None
        self.port = port
        self.passphrase = passphrase
        self.key_filename = key_filename \
            or self._resolve_identity_files(self.server) \
            or self._resolve_identity_files(self.sftp)
        self.filter_file = os.path.join(os.path.dirname(__file__), "config", "messages.yaml")
        self.filtered_patterns = self._load_filtered_patterns()
        self._connect(password=self.password)

    def _create_ssh_client(self):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    @staticmethod
    def _resolve_identity_files(hostname, config_path="~/.ssh/config"):
        """
        Look up the IdentityFile(s) configured for `hostname` in the user's SSH config.

        Paramiko's ``SSHClient.connect`` never reads ``~/.ssh/config``, so a host alias
        that pins a non-default-named key (as VS Code Remote-SSH setups often do) is
        silently ignored and connect() falls back to the ssh-agent or default key
        filenames instead - authenticating with the wrong key and failing silently.

        :param hostname: Host (as passed to `connect`) to look up.
        :type hostname: str
        :param config_path: Path to the SSH config file to consult.
        :type config_path: str
        :return: Expanded identity file paths, or None if none are configured/found.
        :rtype: list[str] | None
        """
        path = os.path.expanduser(config_path)
        if not os.path.isfile(path):
            return None
        try:
            ssh_config = paramiko.SSHConfig()
            with open(path) as f:
                ssh_config.parse(f)
            identity_files = ssh_config.lookup(hostname).get("identityfile")
            if identity_files:
                return [os.path.expanduser(p) for p in identity_files]
        except Exception as e:
            logging.warning(f"⚠️ [_resolve_identity_files]: Could not read {config_path}: {e}")
        return None

    def _connect(self,**kwargs):
        """
        Establish SSH and SFTP connections using Paramiko.

        :raises ConnectionError: If authentication or connection fails.
        """
        self.ssh_client = self._create_ssh_client()
        self.sftp_ssh_client = self._create_ssh_client()
        self.sftp_client = None

        if self.key_filename:
            kwargs.setdefault("key_filename", self.key_filename)
        if self.passphrase:
            kwargs.setdefault("passphrase", self.passphrase)

        try:
            self.ssh_client.connect(self.server, username=self.username, timeout=30, port=self.port, **kwargs)
            self.sftp_ssh_client.connect(self.sftp, username=self.username, timeout=30, port=self.port, **kwargs)
            self.sftp_client = self.sftp_ssh_client.open_sftp()
        except paramiko.AuthenticationException:
            raise ConnectionError(f"❌ [_connect]: Authentication failed for {self.username}@{self.server}.")
        except paramiko.SSHException as e:
            raise ConnectionError(f"❌ [_connect]: SSH connection error: {e}")
        except Exception as e:
            raise ConnectionError(f"❌ [_connect]: Unexpected SSH connection error: {e}")

    def _load_filtered_patterns(self):
        """
        Load SSH output filter patterns from YAML configuration.

        :return: Filter configuration dictionary.
        :rtype: dict
        """
        try:
            with open(self.filter_file, "r") as file:
                return yaml.safe_load(file) or []
        except Exception as e:
            logging.error(f"❌ [_load_filtered_patterns]: Error loading filter file {self.filter_file}: {e}")
            return []

    def filter_output(self, output):
        """
        Filter SSH command output using predefined patterns.

        :param output: Raw output from SSH command.
        :type output: str
        :return: Filtered output string.
        :rtype: str
        """
        if output != "":
            filters = self.filtered_patterns.get("filters", [])
            return "\n".join(
                line for line in output.splitlines() if not any(line.startswith(f) for f in filters)
            )
        return ""

    def run_cmd(self, command):
        """
        Run a command on the remote server via SSH.

        :param command: Command to execute.
        :type command: str
        :return: Dictionary with 'output' and 'err' keys.
        :rtype: dict
        """
        try:
            _, stdout, _ = self.ssh_client.exec_command(command)
            output = stdout.read().decode("utf-8", errors='replace')
            return {"output": self.filter_output(output), "err": None}
        except Exception as e:
            logging.error(f"❌ [run_cmd]: Error executing SSH command {command}: {e}")
            return {"output": None, "err": str(e)}

    def load_h5ad_file(self, path, local_path):
        """
        Download an h5ad file from the remote server in chunks.

        :param path: Remote file path.
        :type path: str
        :param local_path: Destination on local machine.
        :type local_path: str
        :return: Local path of the saved file or None if failed.
        :rtype: str | None
        """
        self.files_to_clean.append(local_path)
        try:
            with self.sftp_client.open(path, 'r') as file:
                with open(local_path, 'wb') as local_file:
                    file.prefetch()
                    for data in iter(lambda: file.read(32768), b''):
                        local_file.write(data)
            return local_path
        except Exception as e:
            logging.error(f"❌ [load_h5ad_file]: Error reading SSH h5ad file {path}: {e}")
            return None

    def _read_file_content(self, path, mode, is_text):
        with self.sftp_client.open(path, mode) as file:
            return file.read()

    def _read_vcf_as_dataframe(self, path):
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "tmp.vcf")
            self.sftp_client.get(path, local_path)
            return self.read_vcf_file_into_df(local_path)

    def listdir(self, path):
        """
        List files and directories at a remote path.

        :param path: Remote directory path.
        :type path: str
        :return: Tuple of (directories, files).
        :rtype: tuple[list[str], list[str]]
        """
        try:
            files, directories = [], []
            for entry in self.sftp_client.listdir_attr(path):
                if S_ISDIR(entry.st_mode):
                    directories.append(entry.filename)
                elif S_ISREG(entry.st_mode):
                    files.append(entry.filename)
            return directories, files
        except Exception as e:
            logging.error(f"❌ [listdir]: Error listing SSH directory {path}: {e}")
            return [], []

    def download_remote_file(self, remote_path, local_path):
        """
        Download a remote file via SFTP.

        :param remote_path: Path on the remote server.
        :type remote_path: str
        :param local_path: Local destination path.
        :type local_path: str
        """
        try:
            self.sftp_client.get(remote_path, local_path)
            print(f"✅ Downloaded: {remote_path} → {local_path}")
        except Exception as e:
            logging.error(f"❌ [download_remote_file]: Error copying SSH file to {local_path}: {e}")
            return None

    def write_to_remote_file(self, data, remote_path, file_format="csv"):
        """
        Write data (string or DataFrame) to a file on the remote server.

        :param data: The data to write.
        :type data: pd.DataFrame | str
        :param remote_path: Destination path on the remote server.
        :type remote_path: str
        :param file_format: Format to use ('csv' supported for DataFrames).
        :type file_format: str
        :raises ValueError: If unsupported DataFrame format is specified.
        :raises TypeError: If data is not string or DataFrame.
        """
        if isinstance(data, pd.DataFrame):
            if file_format in ["csv"]:
                buffer = StringIO()
                data.to_csv(buffer, index=False)
                file_content = buffer.getvalue()
            elif file_format in ["tsv"]:
                buffer = StringIO()
                data.to_csv(buffer, index=False, sep="\t")
                file_content = buffer.getvalue()            
            else:
                raise ValueError("❌ [write_to_remote_file]: Unsupported file format for DataFrame. Use 'csv' or 'tsv'.")
        elif isinstance(data, str):
            file_content = data
        else:
            raise TypeError("❌ [write_to_remote_file]: Data must be a DataFrame or string.")

        try:
            with self.sftp_client.open(remote_path, "w") as remote_file:
                remote_file.write(file_content)
                print(f"✅ Successfully wrote data to {remote_path}")
        except Exception as e:
            logging.error(f"❌ [write_to_remote_file]: Error writing to remote file: {e}")
            return None

    def isfile(self, path):
        """
        Check whether the given remote path points to a file.

        :param path: Remote path.
        :type path: str
        :return: True if path is a file.
        :rtype: bool
        """
        try:
            file_stat = self.sftp_client.lstat(path)
            return file_stat.st_mode & 0o170000 == 0o100000
        except Exception as e:
            logging.error(f"❌ [isfile]: Error checking SSH file type {path}: {e}")
            raise

    def get_file_size(self, path):
        """
        Get the size of a file on the remote server.

        :param path: Remote file path.
        :type path: str
        :return: Size in bytes, or None if error.
        :rtype: int | None
        """
        try:
            return self.sftp_client.stat(path).st_size
        except Exception as e:
            logging.error(f"❌ [get_file_size]: Error reading SSH file size for {path}: {e}")
            return None

    def __del__(self):
        """
        Destructor that closes SSH and SFTP connections and cleans up resources.
        """
        super().__del__()
        self.disconnect()

    def disconnect(self):
        """
        Safely closes active SFTP and SSH connections if they exist.
        Logs an error if any issue occurs during the disconnection.
        """
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.sftp_ssh_client is not None:
                self.sftp_ssh_client.close()
            if self.ssh_client:
                self.ssh_client.close()
        except Exception as e:
            logging.error(f"❌ [disconnect]: Error closing SSH/SFTP connections: {e}")
