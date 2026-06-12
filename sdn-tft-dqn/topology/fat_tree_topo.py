#!/usr/bin/env python3
"""
Fat-tree Topology for SDN Load Balancing
Creates a fat-tree topology with 16 hosts (2 core, 4 aggregation, 8 edge switches)
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time

def create_fat_tree():
    """
    Create a fat-tree topology:
    - 2 core switches (c1, c2)
    - 4 aggregation switches (a1-a4)
    - 8 edge switches (e1-e8)
    - 16 hosts (h1-h16)
    """
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)
    
    info('*** Adding controller\n')
    # Ryu controller running on default port 6633
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    info('*** Adding switches\n')
    # Core switches
    c1 = net.addSwitch('c1', cls=OVSSwitch)
    c2 = net.addSwitch('c2', cls=OVSSwitch)
    
    # Aggregation switches
    a1 = net.addSwitch('a1', cls=OVSSwitch)
    a2 = net.addSwitch('a2', cls=OVSSwitch)
    a3 = net.addSwitch('a3', cls=OVSSwitch)
    a4 = net.addSwitch('a4', cls=OVSSwitch)
    
    # Edge switches
    e1 = net.addSwitch('e1', cls=OVSSwitch)
    e2 = net.addSwitch('e2', cls=OVSSwitch)
    e3 = net.addSwitch('e3', cls=OVSSwitch)
    e4 = net.addSwitch('e4', cls=OVSSwitch)
    e5 = net.addSwitch('e5', cls=OVSSwitch)
    e6 = net.addSwitch('e6', cls=OVSSwitch)
    e7 = net.addSwitch('e7', cls=OVSSwitch)
    e8 = net.addSwitch('e8', cls=OVSSwitch)
    
    info('*** Adding hosts\n')
    # Hosts connected to edge switches (2 hosts per edge switch = 16 hosts)
    hosts = []
    for i in range(1, 17):
        host = net.addHost('h%d' % i, ip='10.0.0.%d/24' % i)
        hosts.append(host)
    
    info('*** Creating links\n')
    # Core to Aggregation links
    # Each core switch connects to all aggregation switches
    for agg in [a1, a2, a3, a4]:
        net.addLink(c1, agg, bw=1000, delay='1ms', loss=0)
        net.addLink(c2, agg, bw=1000, delay='1ms', loss=0)
    
    # Aggregation to Edge links
    # a1 -> e1, e2
    net.addLink(a1, e1, bw=500, delay='2ms', loss=0)
    net.addLink(a1, e2, bw=500, delay='2ms', loss=0)
    # a2 -> e3, e4
    net.addLink(a2, e3, bw=500, delay='2ms', loss=0)
    net.addLink(a2, e4, bw=500, delay='2ms', loss=0)
    # a3 -> e5, e6
    net.addLink(a3, e5, bw=500, delay='2ms', loss=0)
    net.addLink(a3, e6, bw=500, delay='2ms', loss=0)
    # a4 -> e7, e8
    net.addLink(a4, e7, bw=500, delay='2ms', loss=0)
    net.addLink(a4, e8, bw=500, delay='2ms', loss=0)
    
    # Edge to Host links
    # Each edge switch connects to 2 hosts
    for i, edge in enumerate([e1, e2, e3, e4, e5, e6, e7, e8]):
        host_idx = i * 2
        net.addLink(edge, hosts[host_idx], bw=100, delay='1ms', loss=0)
        net.addLink(edge, hosts[host_idx + 1], bw=100, delay='1ms', loss=0)
    
    info('*** Starting network\n')
    net.start()
    
    info('*** Testing connectivity\n')
    net.pingAll()
    
    info('*** Fat-tree topology created successfully\n')
    info('*** Topology: 2 core, 4 aggregation, 8 edge switches, 16 hosts\n')
    info('*** Running CLI (type exit to stop)\n')
    
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_fat_tree()

