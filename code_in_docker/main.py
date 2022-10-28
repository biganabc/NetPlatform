import pexpect
import threading
import os
import json
import requests
import time


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
    def __init__(self, server_ip, user_name, password):
        super().__init__()
        self.mark = False
        self.server_ip = server_ip
        self.user_name = user_name
        self.password = password
        self.error_log = None
        self.child = None

    def setOK(self):
        self.mark = True

    def isOK(self):
        return self.mark

    def run(self):
        try:
            with open("/etc/xl2tpd/xl2tpd.conf", "r") as f:
                str_list = f.readlines()
            for i in range(len(str_list)):
                line = str_list[i]
                if len(line) > 4 and "name" == line[:4]:
                    str_list[i] = "name = " + self.user_name + "\n"
            with open("/etc/xl2tpd/xl2tpd.conf", "w") as f:
                f.writelines(str_list)

            with open("/etc/ppp/peers/testvpn.l2tpd", "r") as f:
                str_list = f.readlines()
            for i in range(len(str_list)):
                line = str_list[i]
                if len(line) > 4 and "user" == line[:4]:
                    str_list[i] = 'user "' + self.user_name + '"\n'
                if len(line) > 8 and "password" == line[:8]:
                    str_list[i] = 'password "' + self.password + '"\n'

            with open("/etc/ppp/peers/testvpn.l2tpd", "w") as f:
                f.writelines(str_list)
            with open("/etc/xl2tpd/xl2tpd.conf", "r") as f:
                str_list = f.readlines()
            for i in range(len(str_list)):
                line = str_list[i]
                if len(line) > 3 and "lns" == line[:3]:
                    str_list[i] = "lns = " + self.server_ip + "\n"
            with open("/etc/xl2tpd/xl2tpd.conf", "w") as f:
                f.writelines(str_list)

            child = pexpect.spawn("xl2tpd")
            time.sleep(0.1)
            # child.expect("\\n")
            child.sendline("chmod +777 /var/run/xl2tpd/l2tp-control")
            time.sleep(0.1)
            # child.expect("\\n")
            child.sendline('echo "c testvpn" >/var/run/xl2tpd/l2tp-control')
            time.sleep(0.1)
            self.child = child
            # child.expect("\\n")
            find_ = False
            for _ in range(3):
                with os.popen("ifconfig") as f:
                    sstr = f.read()
                    if "ppp0" in sstr:
                        find_ = True
                    else:
                        time.sleep(1)
                    print(sstr)
            if not find_:
                print("ppp0网卡未出现")
                self.error_log = "ppp0网卡未出现"
            else:
                print("ppp0网卡出现了")
                self.setOK()
        except Exception as ex:
            self.error_log = str(ex)


if __name__ == "__main__":

    # connectThread = L2tpThread(l2tp_config["service_ip"], l2tp_config["username"], l2tp_config["password"])
    # connectThread.start()
    
    with open("/home/NetPlatform/configurations/task.json", "r") as f:
        task = json.load(f)
    if task["VPNType"] == "openVPN":
        ovpn_config = task["openVPNconfig"]
        connectThread = OpenVPNThread(ovpn_config["configPath"], ovpn_config["username"], ovpn_config["password"])
        connectThread.setDaemon(True)
        connectThread.start()
        connectThread.join()
    elif task["VPNType"] == "l2tp":
        l2tp_config = task["l2tp_config"]
        connectThread = L2tpThread(l2tp_config["service_ip"], l2tp_config["username"], l2tp_config["password"])
        connectThread.start()
        connectThread.join()
    else:
        raise Exception("指令错误 : " + task["VPNType"])
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

    while True:
        time.sleep(0.5)

    if not connectThread.isOK():
        exit(-1)
    os.system("chmod +x /home/NetPlatform/scripts/main")
    os.system("/home/NetPlatform/scripts/main > /home/NetPlatform/temp/log")
