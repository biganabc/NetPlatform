import pexpect
import threading
import os
import json
import requests


def set_DNS_servers(dns_list: list):
    with open("/etc/resolv.conf", "w") as f:
        f.writelines(["nameserver " + str(dns_) + "\n" for dns_ in dns_list])


def get_self_ip():
    s = requests.session()
    s.keep_alive = False
    response = s.get("http://httpbin.org/get", timeout=10)
    result = json.loads(response.text)
    if "origin" not in result:
        return None
    else:
        return result["origin"]


class OpenVPNThread(threading.Thread):
    def __init__(self, file_path, user_name, password):
        super().__init__()
        self.mark = False
        self.file_path = file_path
        self.user_name = user_name
        self.password = password
        self.child = None  # preserve the pexpect object "child" in memory, to avoid pseudo-terminal exiting
        self.error_log = None  #

    def setOK(self):
        self.mark = True

    def isOK(self):
        return self.mark

    def run(self):
        try:
            child = pexpect.spawn("openvpn " + self.file_path)
            child.expect("Enter Auth Username:")
            child.sendline(str(self.user_name))
            child.expect("Enter Auth Password:")
            child.sendline(str(self.password))
            child.expect("Initialization Sequence Completed")
            self.child = child
            self.setOK()
        except Exception as ex:
            self.error_log = str(ex)


class L2tpThread(threading.Thread):
    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    with open("/home/NetPlatform/configurations/task.json", "r") as f:
        task = json.load(f)
    assert task["VPNType"] == "openVPN"  # TODO
    ovpn_config = task["openVPNconfig"]
    connectThread = OpenVPNThread(ovpn_config["configPath"], ovpn_config["username"], ovpn_config["password"])
    connectThread.setDaemon(True)
    connectThread.start()
    connectThread.join()

    ip_info = {
        "ip_str": "0.0.0.0",
        "errors": {}
    }
    if not connectThread.isOK():
        ip_info["errors"]["VPN_error"] = connectThread.error_log
    set_DNS_servers(["114.114.114.114", "8.8.8.8"])
    try:
        ip_str = get_self_ip()
        ip_info["ip_str"] = ip_str
    except Exception as ex:
        ip_info["errors"]["get_ip_error"] = str(ex)
    with open("/home/NetPlatform/temp/ip_info.json", "w") as f:
        json.dump(ip_info, f)
    if not connectThread.isOK():
        exit(-1)
    os.system("chmod +x /home/NetPlatform/scripts/main")
    os.system("/home/NetPlatform/scripts/main > /home/NetPlatform/temp/log")
