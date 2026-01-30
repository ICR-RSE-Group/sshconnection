import logging
from .ssh import SshClient

# def _in_jupyter_notebook():
#     try:
#         from IPython import get_ipython
#         return get_ipython().__class__.__name__ == "ZMQInteractiveShell"
#     except Exception:
#         return False

class SecureSshClient(SshClient):
    """
    SSH client tailored for use within Jupyter notebooks.

    This client enforces key-based authentication only (no password allowed),
    since password authentication is typically disabled or discouraged in
    Jupyter environments for security reasons.

    Parameters:
        server (str): The hostname or IP address of the SSH server.
                      Defaults to "alma.icr.ac.uk".
        username (str): The username to use for SSH login.
        sftp (str): The remote path or hostname for SFTP access.
                    Defaults to "alma-app.icr.ac.uk".
        port (int): SSH port number. Defaults to 22.

    Usage:
        client = SecureSshClient(username="your_username")
        # Connects automatically on initialization using key-based auth.
    """
    def __init__(self, server="alma.icr.ac.uk", username=None, sftp="alma-app.icr.ac.uk", port=22):
        logging.info("🔐 Secure mode: only key-based login allowed.")
        super().__init__(server=server, username=username, password=None, sftp=sftp, port=port, gss_auth=False)

    def __del__(self):
        """
        Destructor that closes SSH and SFTP connections and cleans up resources.
        """
        super().__del__()
