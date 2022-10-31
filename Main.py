import os
import sys
import shutil
import json
import threading
import time
import dns.resolver
import subprocess
import pexpect
import random

DOCKER_IMAGE = "biganabc/client:005"


def dir_initial(docker_name):
    os.makedirs("/home/NetPlatform/temp/" + docker_name)
    os.makedirs("/home/NetPlatform/temp/" + docker_name + "/configurations")
    os.makedirs("/home/NetPlatform/temp/" + docker_name + "/result")
    os.makedirs("/home/NetPlatform/temp/" + docker_name + "/temp")
    # insert code into docker
    shutil.copytree("/home/NetPlatform/code_in_docker", "/home/NetPlatform/temp/" + docker_name + "/Code")
    shutil.copytree("/home/NetPlatform/scripts", "/home/NetPlatform/temp/" + docker_name + "/scripts")


def open_vpn_config_insert(docker_name, openVPN_service, ovpn_config_filename):
    origin_config_path = "/home/NetPlatform/configurations/openVPN/" + openVPN_service + "/ovpn_files/" + ovpn_config_filename
    new_config_path = "/home/NetPlatform/temp/" + docker_name + "/configurations/" + ovpn_config_filename
    shutil.copy(origin_config_path, new_config_path)


class DockerController(threading.Thread):
    def __init__(self, docker_name, image_name):
        super().__init__()
        self.docker_name = docker_name
        self.image_name = image_name
        self.success = False

    def run(self):
        command = "docker run --privileged=true --name=" + self.docker_name + " -v /home/NetPlatform/temp/" + self.docker_name + ":/home/NetPlatform" + " " + self.image_name + " /bin/sh -c 'python3 -u /home/NetPlatform/Code/main.py > /home/NetPlatform/temp/debug'"

        child = pexpect.spawn(command)
        try:
            child.expect(pexpect.EOF, timeout=50)
        except Exception as ex:
            os.system(
                "docker rm -f " + self.docker_name
            )
            print("超时了")
            return
        self.success = True
        os.system(
            "docker rm -f " + self.docker_name
        )
        os.makedirs("/home/NetPlatform/all_results/" + self.docker_name)
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/temp/ip_info.json",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/ip_info.json")
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/result",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/result")
        shutil.rmtree("/home/NetPlatform/temp/" + self.docker_name)
        with open("/home/NetPlatform/all_results/" + self.docker_name + "/ip_info.json") as f:
            ip_dict = json.load(f)
        ip_str = ip_dict["ip_str"]
        print("IP : " + ip_str)
        errors = ip_dict["errors"]
        if errors != {}:
            print("error : " + str(errors))


def readConfigFile():
    with open("Config.json", "r") as f:
        config_dict = json.load(f)
    VPN_dict = {
        "openVPN": {},
        "l2tp": {}
    }
    for open_vpn_service in os.listdir("/home/NetPlatform/configurations/openVPN"):
        VPN_dict["openVPN"][open_vpn_service] = {}
        with open("/home/NetPlatform/configurations/openVPN/" + open_vpn_service + "/user_information.json", "r") as f:
            user_information = json.load(f)
        for key_ in user_information:
            VPN_dict["openVPN"][open_vpn_service][key_] = user_information[key_]
        VPN_dict["openVPN"][open_vpn_service]["routes"] = []
        for ovpn_file_name in os.listdir(
                "/home/NetPlatform/configurations/openVPN/" + open_vpn_service + "/ovpn_files"):
            assert ".ovpn" == ovpn_file_name[-5:]
            VPN_dict["openVPN"][open_vpn_service]["routes"].append(ovpn_file_name)
    for l2tp_vpn_service in os.listdir("/home/NetPlatform/configurations/l2tp"):
        VPN_dict["l2tp"][l2tp_vpn_service] = {}
        with open("/home/NetPlatform/configurations/l2tp/" + l2tp_vpn_service + "/user_information.json", "r") as f:
            user_information = json.load(f)
        for key_ in user_information:
            VPN_dict["l2tp"][l2tp_vpn_service][key_] = user_information[key_]
        VPN_dict["l2tp"][l2tp_vpn_service]["server_list"] = []
        with open("/home/NetPlatform/configurations/l2tp/" + l2tp_vpn_service + "/server_list.json", "r") as f:
            VPN_dict["l2tp"][l2tp_vpn_service]["server_list"] = json.load(f)
        VPN_dict["l2tp"][l2tp_vpn_service]["server_ip_list"] = []

        for server in VPN_dict["l2tp"][l2tp_vpn_service]["server_list"]:
            result = dns.resolver.resolve(server)
            for i in result.response.answer:
                for j in i.items:
                    if j.rdtype == 1:  # 加判断，不然会出现AttributeError: 'CNAME' object has no attribute 'address'
                        VPN_dict["l2tp"][l2tp_vpn_service]["server_ip_list"].append(j.address)

        VPN_dict["l2tp"][l2tp_vpn_service]["server_ip_list"] = list(
            set(
                VPN_dict["l2tp"][l2tp_vpn_service]["server_ip_list"]))

    return config_dict, VPN_dict


def start_ovpn_docker(username, password, service, route):
    docker_name = "ovpn_" + service + "_" + route + "_" + str(time.time())
    dir_initial(docker_name)
    open_vpn_config_insert(docker_name, service, route)
    task_dict = {
        "VPNType": "openVPN",
        "openVPNconfig": {
            "username": username,
            "password": password,
            "configPath": "/home/NetPlatform/configurations/" + route
        }
    }
    # print("username is " + username)
    # print("password is " + password)
    # print("configPath is " + "/home/NetPlatform/configurations/" + route)
    # input("input to continue")
    with open("/home/NetPlatform/temp/" + docker_name + "/configurations/task.json", "w") as f:
        json.dump(task_dict, f)
    docker_controller = DockerController(docker_name, DOCKER_IMAGE)
    docker_controller.start()
    # print("route " + route + " start!")
    docker_controller.join()
    # print("route " + route + " over")


def start_l2tp_docker(username, password, service, server_ip):
    # print("username : " + username)
    # print("password : " + password)
    # print("server_ip : " + server_ip)
    docker_name = "l2tp_" + service + "_" + server_ip + "_" + str(time.time())
    dir_initial(docker_name)
    task_dict = {
        "VPNType": "l2tp",
        "l2tp_config": {
            "username": username,
            "password": password,
            "service_ip": server_ip
        }
    }
    with open("/home/NetPlatform/temp/" + docker_name + "/configurations/task.json", "w") as f:
        json.dump(task_dict, f)
    docker_controller = DockerController(docker_name, DOCKER_IMAGE)
    docker_controller.start()
    # print("l2tp " + service + " " + server_ip + " start")
    docker_controller.join()
    # print("l2tp " + service + " " + server_ip + " over")


class Ovpn_One_Thread(threading.Thread):
    def __init__(self, username, password, service, route, fun):
        super().__init__()
        self.username = username
        self.password = password
        self.service = service
        self.route = route
        self.fun = fun

    def run(self):
        start_ovpn_docker(self.username, self.password, self.service, self.route)
        self.fun("openVPN", self.service)


class L2tp_One_Thread(threading.Thread):
    def __init__(self, username, password, service, server_ip, fun):
        super().__init__()
        self.username = username
        self.password = password
        self.service = service
        self.server_ip = server_ip
        self.fun = fun

    def run(self):
        start_l2tp_docker(self.username, self.password, self.service, self.server_ip)
        self.fun("l2tp", self.service)


class DockerManager:
    def __init__(self, max_thread, connection_dict, task_dict, VPN_dict):
        self.max_thread = max_thread
        self.pool = max_thread  # 剩余最大线程数
        self.connection_dict = connection_dict  # 剩余允许连接数
        self.task_dict = task_dict  # 剩余任务数
        self.lock = threading.Lock()
        self.VPN_dict = VPN_dict
        self.ovpn_route_indexes = {}
        self.l2tp_id_indexes = {}
        if "openVPN" in self.VPN_dict:
            for service in self.VPN_dict["openVPN"]:
                self.ovpn_route_indexes[service] = 0
        if "l2tp" in self.VPN_dict:
            for service in self.VPN_dict["l2tp"]:
                self.l2tp_id_indexes[service] = 0

    def have_task(self):
        for protocol in self.task_dict:
            for service in self.task_dict[protocol]:
                if self.task_dict[protocol][service] > 0:
                    return True
        return False

    def get_task(self):
        self.lock.acquire()
        for protocol in self.task_dict:
            for service in self.task_dict[protocol]:
                if self.task_dict[protocol][service] > 0 and self.connection_dict[protocol][
                    service] > 0 and self.pool > 0:
                    self.task_dict[protocol][service] -= 1
                    self.connection_dict[protocol][service] -= 1
                    self.pool -= 1
                    self.lock.release()
                    return protocol, service
        self.lock.release()
        return None

    def finish(self, protocol, service):
        print("协议 " + protocol + " 服务 " + service + " 的一个线程结束了")
        self.lock.acquire()
        self.connection_dict[protocol][service] += 1
        self.pool += 1
        self.lock.release()

    def start_one_thread(self, protocol, service):
        print("即将开启协议 " + protocol + " 服务 " + service + " 的一个线程")
        if protocol == "openVPN":
            ovpn_route_index = self.ovpn_route_indexes[service]
            self.ovpn_route_indexes[service] += 1
            self.ovpn_route_indexes[service] %= len(self.VPN_dict["openVPN"][service]["routes"])
            ovpn_thread = Ovpn_One_Thread(self.VPN_dict["openVPN"][service]["username"],
                                          self.VPN_dict["openVPN"][service]["password"],
                                          service,
                                          self.VPN_dict["openVPN"][service]["routes"][ovpn_route_index],
                                          self.finish)
            ovpn_thread.start()
        elif protocol == "l2tp":
            l2tp_ip_index = self.l2tp_id_indexes[service]
            self.l2tp_id_indexes[service] += 1
            self.l2tp_id_indexes[service] %= len(self.VPN_dict["l2tp"][service]["server_ip_list"])
            l2tp_thread = L2tp_One_Thread(self.VPN_dict["l2tp"][service]["username"],
                                          self.VPN_dict["l2tp"][service]["password"],
                                          service,
                                          self.VPN_dict["l2tp"][service]["server_ip_list"][l2tp_ip_index],
                                          self.finish)
            l2tp_thread.start()
        else:
            raise Exception("错误的协议名")

    def start(self):
        while True:
            print("寻找任务")
            if not self.have_task():
                print("无任务")
                break
            task = self.get_task()
            if task is None:
                print("找不到任务")
                time.sleep(5)
                continue
            print("即将安排任务")
            protocol = task[0]
            service = task[1]
            self.start_one_thread(protocol, service)
        while True:
            bool_ = False
            self.lock.acquire()
            if self.pool == self.max_thread:
                bool_ = True
            self.lock.release()
            if not bool_:
                time.sleep(5)
            else:
                break


if __name__ == "__main__":
    config_dict, VPN_dict = readConfigFile()

    my_task = {"openVPN": {}, "l2tp": {}}
    connection_dict = {"openVPN": {}, "l2tp": {}}

    # TASK
    for service in VPN_dict["openVPN"]:
        my_task["openVPN"][service] = 200
    for service in VPN_dict["l2tp"]:
        my_task["l2tp"][service] = 200

    # route
    for service in VPN_dict["openVPN"]:
        random.shuffle(VPN_dict["openVPN"][service]["routes"])
    for service in VPN_dict["l2tp"]:
        random.shuffle(VPN_dict["l2tp"][service]["server_ip_list"])

    # connection
    for service in VPN_dict["openVPN"]:
        connection_dict["openVPN"][service] = 1
    for service in VPN_dict["l2tp"]:
        connection_dict["l2tp"][service] = 1
    print(connection_dict)
    print(my_task)
    DockerManager(10, connection_dict, my_task, VPN_dict).start()

    # for _ in range(config_dict["openVPN"]["global_epoch"]):
    #     for service in VPN_dict["openVPN"]:
    #         username = VPN_dict["openVPN"][service]["username"]
    #         password = VPN_dict["openVPN"][service]["password"]
    #         ovpn_list = VPN_dict["openVPN"][service]["routes"]
    #         for route in ovpn_list:
    #             start_ovpn_docker(username, password, service, route)
    # for _ in range(config_dict["l2tp"]["global_epoch"]):
    #     for service in VPN_dict["l2tp"]:
    #         username = VPN_dict["l2tp"][service]["username"]
    #         password = VPN_dict["l2tp"][service]["password"]
    #         server_ip_list = VPN_dict["l2tp"][service]["server_ip_list"]
    #         for server_ip in server_ip_list:
    #             start_l2tp_docker(username, password, service, server_ip)
