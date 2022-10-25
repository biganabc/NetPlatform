from scapy.all import *
import os


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
    try:
        ls(p)
        result = sr(p, verbose=0, timeout=2)
    except Exception as ex:
        return str(ex)
    return result


if __name__ == "__main__":
    os.system("dig baidu.com @114.114.114.114")
    print("===" * 50)
    os.system("dig baidu.com @8.8.8.8")
    print("===" * 50)
    os.system("dig baidu.com @39.156.66.10")
    print("===" * 50)
    os.system("dig baidu.com @106.11.172.9")
