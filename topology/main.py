from __future__ import annotations

import argparse
from time import sleep

from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo


def main():
    args = parse()

    setLogLevel(args.log)

    net = Mininet(
        topo=DisasterResistantNetworkTopo(),
        controller=RemoteController("c0", port=6633),
    )
    receiver, sender = net.hosts[0], net.hosts[1]
    switches = net.switches

    net.start()

    setup(receiver, switches)
    net.pingAll()

    run_disaster(receiver, sender, switches)

    net.stop()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


# prepare for back up data
def setup(receiver, switches):
    for s in switches:
        s.vsctl('set bridge', s, 'stp-enable=true')

    receiver.cmd(f"./bin/server -v > server/server.log 2>&1 &")
    # receiver.cmd(f"./bin/server -v > server/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log &")

    info('*** waiting to set STP...\n')
    sleep(30)


def run_disaster(receiver, sender, switches):
    info("*** Disaster was predicted and start emergency backup!\n")
    sender.cmd(f"./bin/client -addr {receiver.IP()}:44300 -chunk 1G.txt > client/client.log 2>&1 &")

    # time until disaster arrives
    sleep(10)

    # disaster arrives
    info("*** Link between s1 and s2 is being swept by tsunami...\n")
    switches[0].cmd("ovs-vsctl del-port s1-eth1")
    switches[0].cmd("ovs-vsctl del-port s2-eth1")


if __name__ == "__main__":
    main()
