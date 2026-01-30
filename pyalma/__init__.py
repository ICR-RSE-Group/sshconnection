# pyalma/__init__.py
from .cli import main 
from .local import LocalFileReader
from .ssh import SshClient
from .securessh import SecureSshClient
from .kerberos import KerberosClient
from .pdfreader import read_pdf_to_dataframe,read_pdf_as_text
from importlib.metadata import version, PackageNotFoundError
from pyalma.debug import setup_paramiko

setup_paramiko(debug=False)

try:
    __version__ = version("pyalma")
except PackageNotFoundError:
    __version__ = "unknown"