import os
import sys
import shutil
import json
import threading
import time


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

    def run(self):
        command = "docker run --privileged=true --name='" + self.docker_name + "' -v /home/NetPlatform/temp/" + self.docker_name + ":/home/NetPlatform" + " " + self.image_name + " /bin/sh -c 'python3 /home/NetPlatform/Code/main.py'"
        print(command)
        os.system(command)
        print("docker is over")
        os.system(
            "docker rm " + self.docker_name
        )
        os.makedirs("/home/NetPlatform/all_results/" + self.docker_name)
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/temp/ip_info.json",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/ip_info.json")
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/result",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/result")
        shutil.rmtree("/home/NetPlatform/temp/" + self.docker_name)


def readConfigFile():
    with open("Config.json", "r") as f:
        config_dict = json.load(f)
    VPN_dict = {
        "openVPN": {}
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
    return config_dict, VPN_dict


def start_ovpn_docker(username, password, service, route):
    docker_name = "ovpn_" + service + "_" + route + "_" + str(int(time.time()))
    dir_initial(docker_name)
    open_vpn_config_insert(docker_name, "PureVPN", "ae2-ovpn-tcp.ovpn")
    task_dict = {
        "VPNType": "openVPN",
        "openVPNconfig": {
            "username": username,
            "password": password,
            "configPath": "/home/NetPlatform/configurations/" + route
        }
    }
    print("username is "+username)
    print("password is "+password)
    print("configPath is "+"/home/NetPlatform/configurations/" + route)
    input("input to continue")
    with open("/home/NetPlatform/temp/" + docker_name + "/configurations/task.json", "w") as f:
        json.dump(task_dict, f)
    docker_controller = DockerController(docker_name, "biganabc/client:005")
    docker_controller.start()
    print("route " + route + " start!")
    docker_controller.join()
    print("route " + route + " over")


if __name__ == "__main__":
    config_dict, VPN_dict = readConfigFile()
    for _ in range(config_dict["openVPN"]["global_epoch"]):
        for service in VPN_dict["openVPN"]:
            username = VPN_dict["openVPN"][service]["username"]
            password = VPN_dict["openVPN"][service]["password"]
            ovpn_list = VPN_dict["openVPN"][service]["routes"]
            for route in ovpn_list:
                start_ovpn_docker(username, password, service, route)
