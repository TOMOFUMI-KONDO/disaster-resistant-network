from __future__ import annotations

import argparse
from time import sleep

from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from enums import Network


def main():
    args = parse()
    setLogLevel(args.log)

    for n in [Network.TCP, Network.QUIC]:
        run_experiment(n)


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


def run_experiment(network: Network):
    net = Mininet(
        topo=DisasterResistantNetworkTopo(),
        controller=RemoteController("c0", port=6633),
    )
    receiver, sender = net.hosts[0], net.hosts[1]
    switches = net.switches

    net.start()

    setup(receiver, switches, network)
    net.pingAll()

    run_disaster(receiver, sender, switches, network)
    CLI(net)

    net.stop()


# prepare for back up data
def setup(receiver, switches, network: Network):
    for s in switches:
        s.vsctl('set bridge', s, 'stp-enable=true')

    network_name = network.name.lower()
    receiver.cmd(f"./bin/{network_name}/server -v > log/server_{network_name}.log 2>&1 &")
    # receiver.cmd(f"./bin/server -v > server/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log &")

    info('*** waiting to set STP...\n')
    sleep(60)


def run_disaster(receiver, sender, switches, network: Network):
    info("*** Disaster was predicted and start emergency backup!\n")
    network_name = network.name.lower()
    sender.cmd(f"./bin/{network_name}/client -addr {receiver.IP()}:44300 -chunk 1G.txt "
               f"> log/client_{network_name}.log 2>&1 &")

    # time until disaster arrives
    sleep(10)

    # disaster arrives
    info("*** Link between s1 and s2 is being swept by tsunami...\n")
    switches[0].cmd("ovs-vsctl del-port s1-eth1")
    switches[0].cmd("ovs-vsctl del-port s2-eth1")

    sleep(60)
    info("*** Link between s3 and s4 is being swept by tsunami...\n")
    switches[0].cmd("ovs-vsctl del-port s3-eth2")
    switches[0].cmd("ovs-vsctl del-port s4-eth2")


if __name__ == "__main__":
    main()
