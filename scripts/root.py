import json
from scapy.all import *
import dns.message
import dns.query
import requests
import time
import pandas

roots = ["198.41.0.4",
         "199.9.14.201",
         "192.33.4.12",
         "199.7.91.13",
         "192.203.230.10",
         "192.5.5.241",
         "192.112.36.4",
         "198.97.190.53",
         "192.36.148.17",
         "192.58.128.30",
         "193.0.14.129",
         "199.7.83.42",
         "202.12.27.33"]

str_set = set()
all_chars = "abcdefghijklmnopqrstuvwxyz1234567890"


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


def getRandomStr():
    global str_set, all_chars
    while True:
        rand_len = random.randint(8, 12)
        chars = []
        for _ in range(rand_len):
            chars.append(random.choice(all_chars))
        result_ = "".join(chars)
        if result_ not in str_set:
            str_set.add(result_)
            return result_


def dns_trace2(ip_str: str,
               src_port=53,
               ip_id=64,
               time_out=1,  # 默认超时时间是1秒
               ) -> list:
    def make_dns_packet(ttl):
        a = IP(id=ip_id, dst=ip_str, ttl=ttl)
        b = UDP(sport=src_port, dport=53)
        c = DNS(id=ttl, qr=0, opcode=0, tc=0, rd=1, qdcount=1, ancount=0, nscount=0, arcount=1)
        c.qd = DNSQR(qname="baidu.com", qtype=1, qclass=1)
        old_list = DNSRROPT.fields_desc
        new_list = [_ for _ in old_list]
        new_list[5] = BitEnumField("z", 0, 16, {0: "D0"})
        DNSRROPT.fields_desc = new_list
        c.ar = DNSRROPT(0)
        p = a / b / c
        DNSRROPT.fields_desc = old_list
        return p

    conf.route = Route()
    conf.ifaces.reload()
    list_ = []  # 分别是ttl = 1,2,3,....
    for ttl in range(1, 64):
        dns_packet = make_dns_packet(ttl)
        # ls(dns_packet)
        # print(if_list)
        result = None
        for iface in if_list:
            try:
                result = sr(dns_packet, verbose=0, timeout=time_out, iface=iface)
                if len(result[0]) != 0:
                    break
            except Exception as ex:
                print(ex)
                continue
        if result is None:
            print("没有网卡")
            raise Exception("请与管理员联系，没有网卡")
        if len(result[0]) == 0:
            print("ttl = " + str(ttl) + " " + "超时无应答")
            list_.append("None")
        else:
            print("ttl = " + str(ttl) + " " + result[0][0].answer.src)
            ip_addr = result[0][0].answer.src
            list_.append(ip_addr)
            if ip_addr == ip_str:
                break
    return list_


def dns_query(qname, type_, class_, target, pool, note, wantdns=False):
    try:
        start_time = time.time()
        result = str(dns.query.udp(
            dns.message.make_query(qname, type_, class_, want_dnssec=wantdns),
            target,
            timeout=2
        ))
        end_time = time.time()
        cost_time = end_time - start_time
    except Exception as ex:
        result = str(ex)
        cost_time = ""
    pool.append([
        qname, type_, class_, target, result, note, str(wantdns), cost_time
    ])


ipv4 = get_self_ip()
if ipv4 is None:
    exit(0)
pool = []
dns_query(getRandomStr() + ".youtube.com", "A", "IN", "39.156.66.10", pool, "2.1")
dns_query(getRandomStr() + ".youtube.com", "A", "IN", "106.11.172.9", pool, "2.1")
print("DNS劫持检测完成")
for _ in range(5):
    for root in roots:
        dns_query(getRandomStr() + ".youtube.com", "A", "IN", root, pool, "2.2")
for _ in range(5):
    for root in roots:
        dns_query(getRandomStr() + ".baidu.com", "A", "IN", root, pool, "2.3")
for root in roots:
    dns_query("version.bind", "TXT", "CH", root, pool, "2.4")
for root in roots:
    dns_query("id.server", "TXT", "CH", root, pool, "2.4")
for root in roots:
    dns_query(".", "NS", "IN", root, pool, "2.4")
print("第二部分完成")
for root in roots:
    for kind_ in ["com", "net", "org", "top", "us", "uk", "cn", "ru"]:
        dns_query(kind_, "A", "IN", root, pool, "4.1")
for root in roots:
    dns_query(getRandomStr() + ".example", "A", "IN", root, pool, "4.2")
for root in roots:
    dns_query(".", "A", "IN", root, pool, "4.3", wantdns=True)
print("第四部分完成")
for _ in range(5):
    print("第一轮追踪")
    for root in roots:
        print("正在追踪" + root)
        try:
            result = dns_trace2(root)
        except Exception as ex:
            print(ex)
            break
        pool.append(["traceroute", "", "", root, result, "3.1", "", ""])
print("工作正常结束")

ipv4_2 = get_self_ip()
if ipv4 != ipv4_2:  # IP地址变了，说明代理失效了
    exit(0)

with open("home/NetPlatform/result/" + ipv4 + ".json", "w") as f:
    json.dump(list_, f)
