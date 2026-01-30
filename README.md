# Pyalma

A Python library for SSH connections and remote command execution using Paramiko.
## To Install pyalma using pip (no need to download the code)
Run the following in your Python environment:
```bash
pip install "pyalma @ git+https://github.com/ICR-RSE-Group/pyalma.git@main"
```
## To build and install the package locally:
1. Clone this repo locally to your machine:
Make sure to navigate to the package directory before building
```bash
git clone git@github.com:ICR-RSE-Group/pyalma.git
cd pyalma
```

2. Create a Python Environment and activate it:
Before building and installing the package, it is recommended to create a dedicated Python environment for your project.
```bash
python -m venv .env-py
source .env-py/bin/activate
```

3. Install Build Dependencies
```bash
python -m pip install --upgrade pip build
```

4. Build the Package Locally:
```bash
python -m build
```

5. Install locally using `pip`:
```bash
pip install -e .
```

### For command line,
```bash
pyalma-cli --cmd "ls -l"
```
## For remote access, from within python
```
from pyalma import SshClient

ssh = SshClient(server='your_server', username='your_username', password='your_password')
result = ssh.run_cmd('ls -l')
print(result["output"])
print(result["err"])
```

## For remote access using Ssh Keys, from within python or jupyter notebooks
```
from pyalma import SecureSshClient

secure_ssh = SecureSshClient(server='your_server', username='your_username')
result = ssh.run_cmd('ls -l')
print(result["output"])
print(result["err"])
```

## For remote access using Kerberos authentication
Kerberos requires a valid ticket on the local host before attempting a connection. To create a Ticket Granting Ticket (TGT), run:
```bash
kinit msarkis@ICR.AC.UK
```
* Replace msarkis with your actual username.
* This generates a Ticket Granting Ticket (TGT) with a default validity of 10 hours.
* You will need to renew or recreate the ticket once it expires.

```
from pyalma import KerberosClient
kerberos_ssh = KerberosClient(server="your_server", username="your_username")
result = kerberos_ssh.run_cmd("ls -l")
print(result["output"])
print(result["err"])
```

Notes:

* This authentication method only works with servers that support Kerberos.
* At ICR, a test server sjane is available for experimenting.
* When you SSH using gssapi-with-mic, the client automatically requests a service ticket for host/sjane@ICR.AC.UK from the Kerberos Key Distribution Center (KDC).


## For local access, from within python
```
from pyalma import LocalFileReader

local = LocalFileReader()
result = local.run_cmd('ls -l')
print(result["output"])
print(result["err"])
```

# To read remote anndata files, from within python:
```
remote_path = "/full/remote/path/file.h5ad"
local_path = "local_copy.h5ad"
ssh = SshClient(server='your_server', username='your_username', password='your_password')
ssh.load_h5ad_file(path, local_path)
adata = ssh.read_h5ad(local_path)
print(adata)
```

# To read pdf files, from within python:
```
path = "file.pdf"
ssh = SshClient(server='your_server', username='your_username', password='your_password')
# Read PDF into a DataFrame using pyalma
pdf_df = ssh.read_file_into_df(path,'pdf')
# returned dataframe contains three columns : "Page", "Content" and "Images"
```



# Setting Up SSH Keys for `SecureSshClient`
## Generate a new SSH key:
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```
## Add Your SSH Key to the Remote Server:
Access and copy the newly generated public key via:
```bash
cat ~/.ssh/id_rsa.pub
```
Then paste it into the remote server’s `~/.ssh/authorized_keys` file.

## Test the setup
Before using the Python client, confirm the connection works:
```bash
ssh your_username@alma.icr.ac.uk
```
You should connect without a password prompt

