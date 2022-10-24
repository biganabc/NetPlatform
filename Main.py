import os
import sys
import shutil
import json
import threading


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
        os.makedirs("/home/NetPlatform/all_results/" + self.docker_name)
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/ip_info.json",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/ip_info.json")
        shutil.move("/home/NetPlatform/temp/" + self.docker_name + "/result",
                    "/home/NetPlatform/all_results/" + self.docker_name + "/result")
        os.system(
            "docker rm " + self.docker_name
        )


if __name__ == "__main__":
    DOCKER_NAME = sys.argv[1]
    dir_initial(DOCKER_NAME)
    open_vpn_config_insert(DOCKER_NAME, "PureVPN", "ae2-ovpn-tcp.ovpn")
    task_dict = {
        "VPNType": "openVPN",
        "openVPNconfig": {
            "username": "purevpn0s11829139",
            "password": "Urom688DosIYZM",
            "configPath": "/home/NetPlatform/configurations/ae2-ovpn-tcp.ovpn"
        }
    }

    with open("/home/NetPlatform/temp/" + DOCKER_NAME + "/configurations/task.json", "w") as f:
        json.dump(task_dict, f)
    print("file initial over")
    DockerController(DOCKER_NAME, "biganabc/client:005").start()
