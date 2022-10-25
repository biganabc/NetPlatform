from scapy.all import *
import os
import time
import json
import requests

def get_self_ip():
    s = requests.session()
    s.keep_alive = False
    try:
        response = s.get("http://httpbin.org/get", timeout=10)
        result = json.loads(response.text)
    except Exception as ex:
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
    a = IP(dst=ip_dst)
    b = UDP(dport=53)
    c = DNS(qr=0, opcode=0, tc=0, rd=1, qdcount=1, ancount=0, nscount=0, arcount=1)
    c.qd = DNSQR(qname=qname, qtype=1, qclass=1)
    old_list = DNSRROPT.fields_desc
    new_list = [_ for _ in old_list]
    new_list[5] = BitEnumField("z", 0, 16, {0: "D0"})
    DNSRROPT.fields_desc = new_list
    c.ar = DNSRROPT(0)
    p = a / b / c
    DNSRROPT.fields_desc = old_list
    print("查询报文:")
    ls(p)
    result = sr(p, verbose=0, timeout=2)
    if len(result[0]) == 0:
        print("无应答")
        return p, ""
    IP_ = result[0][0].answer["IP"]
    print("应答报文:")
    ls(IP_)

    return p, IP_


if __name__ == "__main__":
    self_ip_str = get_self_ip()
    if self_ip_str is None:
        self_ip_str = "0.0.0.0"
    send_packet, receive_packet = queryDNS("202.112.51.108",
                                           self_ip_str + "." + str(int(time.time())) + ".queryrecord.com")
    send_p_str = packet2str(send_packet)
    if receive_packet != "":
        receive_p_str = packet2str(receive_packet)
    else:
        receive_p_str = ""
    with open("my_packets.json", "w") as f:
        json.dump([send_p_str, receive_p_str], f)
