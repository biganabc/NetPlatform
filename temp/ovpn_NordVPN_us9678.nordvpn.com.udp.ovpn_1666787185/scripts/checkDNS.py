from scapy.all import *
import os
import time
import json
import requests
import base64


def get_self_ip():
    s = requests.session()
    s.keep_alive = False
    try:
        response = s.get("http://httpbin.org/get", timeout=10)
        result = json.loads(response.text)
    except Exception as ex:
        print(ex)
        return None
    if "origin" not in result:
        return None
    else:
        return result["origin"]


def packet2str(packet):
    bytes_of_packet = raw(packet)  # IP数据报的字节码序列
    base64_of_packet = base64.b64encode(bytes_of_packet).decode()  # 直接得到的base64对象是bytes类型，首先解码为str类型
    return base64_of_packet


def str2packet(packet_str):
    p = base64.b64decode(packet_str.encode())
    ip_packet = IP(p)
    return ip_packet


def queryDNS(ip_dst, qname):
    p = IP(dst=ip_dst) / UDP(sport=RandShort(), dport=53) / DNS(rd=1, qd=DNSQR(qname=qname, qtype="A"))
    print("查询报文:")
    ls(p)
    result = sr1(p, verbose=0, timeout=3)
    if result is None:
        print("无应答")
    else:
        print("应答报文")
        ls(result)
    return p, result


if __name__ == "__main__":
    self_ip_str = get_self_ip()
    if self_ip_str is None:
        self_ip_str = "0.0.0.0"
    all_results = {
        "202.112.51.108": [],
        "39.156.66.10": [],
        "106.11.172.9": [],
        "114.114.114.114": [],
        "8.8.8.8": []
    }
    for i in range(5):
        for ip_str in all_results:
            send_packet, receive_packet = queryDNS(ip_str,
                                                   self_ip_str + "." + ip_str + "." + str(
                                                       time.time()) + "." + str(i) + ".queryrecord.com")
            send_p_str = packet2str(send_packet)
            if receive_packet is not None:
                receive_p_str = packet2str(receive_packet)
            else:
                receive_p_str = ""
            all_results[ip_str].append([send_p_str, receive_p_str])
            if ip_str == "202.112.51.108":
                continue
            send_packet, receive_packet = queryDNS(ip_str, "baidu.com")
            send_p_str = packet2str(send_packet)
            if receive_packet is not None:
                receive_p_str = packet2str(receive_packet)
            else:
                receive_p_str = ""
            all_results[ip_str].append([send_p_str, receive_p_str])
    # query_name = self_ip_str + "." + "202.112.51.108" + "." + str(time.time()) + "." + "0" + ".queryrecord.com"
    # os.system("dig " + query_name + " @202.112.51.108")
    with open("/home/NetPlatform/result/my_packets.json", "w") as f:
        json.dump(all_results, f)
