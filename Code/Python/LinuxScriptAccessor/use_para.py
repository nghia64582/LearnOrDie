import paramiko
from time import time
from paramiko import RSAKey, Ed25519Key, ECDSAKey
from paramiko.ssh_exception import SSHException
import re
from datetime import datetime
import getpass
import random

# === CONFIGURATION ===
REMOTE_HOST = 'dev.sandinhstudio.com'
USERNAME = 'nghiavt'
KEY_PATH = 'C:/Users/NghiaVT/.ssh/id_rsa'
KEY_PASSPHRASE = getpass.getpass(prompt='Passphrase: ', stream=None)  # Optional
REMOTE_LOG_DIR = '/mnt/hdd2/f1chanlogs'
LOG_PREFIX = 'smartfox.log.'

# Define your time range (inclusive)
START_DATE = datetime(2025, 4, 8)
END_DATE = datetime(2025, 4, 8)

def load_private_key(path, password=None):
    for key_class in [RSAKey, Ed25519Key, ECDSAKey]:
        try:
            return key_class.from_private_key_file(path, password=password)
        except SSHException:
            continue
    raise Exception("Unsupported or invalid SSH key format.")

def connect_ssh():
    key = load_private_key(KEY_PATH, password=KEY_PASSPHRASE)
    # key = paramiko.RSAKey.from_private_key_file(KEY_PATH, password=KEY_PASSPHRASE)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(REMOTE_HOST, username=USERNAME, pkey=key)
    return ssh

def list_log_files(ssh):
    stdin, stdout, stderr = ssh.exec_command(f'ls {REMOTE_LOG_DIR}')
    files = stdout.read().decode().splitlines()
    return [f for f in files if f.startswith(LOG_PREFIX)]

def filter_by_date(filenames):
    filtered = []
    for name in filenames:
        match = re.search(r'smartfox\.log\.(\d{4}-\d{2}-\d{2})(-\d{2})?', name)
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                if START_DATE <= file_date <= END_DATE:
                    filtered.append(name)
            except ValueError:
                continue
    return filtered

def read_and_analyze_files(ssh: paramiko.SSHClient, filenames):
    for filename in filenames:
        startTime = time()
        path = f"{REMOTE_LOG_DIR}/{filename}"
        print(f"\n🔍 Reading {path}")
        keyword = "freeCoinVer"
        stdin, stdout, stderr = ssh.exec_command(f'grep "{keyword}" {path}')
        lines = stdout.read().decode().splitlines()
        print(f"Read all lines in file after {(time() - startTime)} seconds")
        listB = []
        for i in range(len(lines)):
            line = lines[i]
            try:
                match = re.search(r'b=(\d+).*?isSkip=([a-zA-Z0-9_]+)', line)
                if match:
                    b = int(match.group(1))
                    isSkip = match.group(2)
                    if isSkip == "true":
                        print(line)
                        listB.append(b)
                else:
                    pass
            except IndexError:
                continue
        print(f"✅ Finished analyzing {filename}, total b with isSkip=true: {sum(listB)}")

if __name__ == '__main__':
    ssh = connect_ssh()
    all_files = list_log_files(ssh)
    filtered_files = filter_by_date(all_files)
    print(f"📄 Files in date range: {filtered_files}")
    read_and_analyze_files(ssh, filtered_files)
    ssh.close()