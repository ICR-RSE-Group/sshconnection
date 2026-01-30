import logging
from .ssh import SshClient

class KerberosClient(SshClient):
    """
    This client enforces kerberos authentication only (no password or ssh key allowed)

    Parameters:
        server (str): The hostname or IP address of the SSH server.
                      Defaults to "alma.icr.ac.uk".
        username (str): The username to use for SSH login.
        sftp (str): The remote path or hostname for SFTP access.
                    Defaults to "alma-app.icr.ac.uk".
        port (int): SSH port number. Defaults to 22.

    Usage:
        client = KerberosClient(username="your_username")
        # Connects automatically on initialization using key-based auth.
    """
    def __init__(self, server="alma.icr.ac.uk", username=None, sftp="alma-app.icr.ac.uk", port=22, gss_auth=True):
        logging.info(" Kerberos-based login activated.")
        super().__init__(server=server, username=username, password=None, sftp=sftp, port=port, gss_auth=gss_auth)

    def __del__(self):
        """
        Destructor that closes SSH and SFTP connections and cleans up resources.
        """
        super().__del__()
