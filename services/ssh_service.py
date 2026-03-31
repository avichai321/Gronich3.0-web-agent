import re
import time
import paramiko


class SSHService:
    @staticmethod
    def execute_command(hostname: str, username: str, password: str, command: str) -> tuple[str, str]:
        output = ""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=15,
            )

            _, stdout, stderr = client.exec_command(command, timeout=20)
            output = stdout.read().decode(errors="ignore")
            error = stderr.read().decode(errors="ignore")

            client.close()
            return output.strip(), error.strip()

        except Exception as exc:
            return output.strip(), str(exc)


class IOSShell:
    def __init__(self, ip: str, username: str, password: str, prompt_regex=b"[>#] *$", timeout: int = 10):
        self.ip = ip
        self.username = username
        self.password = password
        self.prompt_regex = re.compile(prompt_regex, re.M)
        self.timeout = timeout
        self.client = None
        self.chan = None

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            self.ip,
            username=self.username,
            password=self.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=self.timeout,
        )
        self.chan = self.client.invoke_shell(width=200, height=40)
        self.chan.settimeout(self.timeout)
        self._read_until_prompt()
        self.send("terminal length 0")
        self._read_until_prompt()

    def close(self):
        try:
            if self.chan:
                self.chan.close()
        finally:
            if self.client:
                self.client.close()

    def send(self, cmd: str):
        if not cmd.endswith("\n"):
            cmd += "\n"
        self.chan.send(cmd)

    def _read_until_prompt(self, extra_timeout=None):
        buf = b""
        end = time.time() + (extra_timeout or self.timeout)

        while time.time() < end:
            try:
                if self.chan.recv_ready():
                    chunk = self.chan.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if self.prompt_regex.search(buf):
                        return buf
                else:
                    time.sleep(0.02)
            except Exception:
                time.sleep(0.05)

        return buf

    def run(self, cmd: str, wait: float = 0.5):
        self.send(cmd)
        if wait:
            time.sleep(wait)
        return self._read_until_prompt()


def run_ios_commands(hostname: str, username: str, password: str, command_seq: list[str]) -> tuple[str, str]:
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    output = ""

    try:
        ssh_client.connect(
            hostname,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )

        remote_shell = ssh_client.invoke_shell()
        time.sleep(0.5)

        for command in command_seq:
            remote_shell.send(command + "\n")
            time.sleep(0.25)

        time.sleep(1)
        while remote_shell.recv_ready():
            output += remote_shell.recv(65535).decode("utf-8", errors="ignore")
            time.sleep(0.1)

        return output, ""

    except Exception as exc:
        return output, str(exc)
    finally:
        ssh_client.close()


def reset_interface_and_apply(ip: str, username: str, password: str, interface: str, new_commands: list[str], shut: bool) -> tuple[bool, str]:
    shell = IOSShell(ip, username, password)
    try:
        shell.connect()
        output = shell.run(f"show running-config interface {interface}")

        desc_line = ""
        for line in output.decode(errors="ignore").splitlines():
            clean = line.strip()
            if clean.startswith("description "):
                desc_line = clean
                break

        shell.run("configure terminal")
        shell.run(f"default interface {interface}")
        shell.run(f"interface {interface}")

        if desc_line:
            shell.run(desc_line)

        for cmd in new_commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd.lower().startswith(("end", "exit", "wr", "write ")):
                continue
            shell.run(cmd)

        if shut:
            shell.run("shutdown")

        shell.run("end")
        shell.run("write memory", wait=1.0)
        return True, f"Applied config on {interface}"

    except Exception as exc:
        return False, str(exc)

    finally:
        try:
            shell.close()
        except Exception:
            pass