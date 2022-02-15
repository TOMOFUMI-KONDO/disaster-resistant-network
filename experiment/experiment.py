from time import sleep

from mininet.cli import CLI
from mininet.log import info
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from disaster_scheduler import DisasterScheduler
from enums import Network


class Experiment(object):
    def __init__(self, network: Network):
        self.__network = network
        self.__net = Mininet(
            topo=DisasterResistantNetworkTopo(),
            controller=RemoteController("c0", port=6633),
        )
        hosts = self.__net.hosts
        self.__receiver, self.__sender = hosts[0], hosts[1]
        self.__disaster_scheduler = DisasterScheduler(self.__net.switches)

    def run(self):
        self.__net.start()

        self.__set_stp()
        self.__prepare_backup()
        self.__net.pingAll()

        # assume that disaster was detected
        self.__start_backup()
        self.__disaster_scheduler.run()

        CLI(self.__net)

        self.__net.stop()

    # prepare for back up data
    def __set_stp(self):
        for s in self.__net.switches:
            s.vsctl('set bridge', s, 'stp-enable=true')

        info('*** waiting to set STP...\n')
        sleep(60)

    def __prepare_backup(self):
        network_name = self.__network_name()
        self.__receiver.cmd(f"./bin/{network_name}/server -v > log/server_{network_name}.log 2>&1 &")
        # receiver.cmd(f"./bin/server -v > server/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log &")

        info('*** waiting to boot server...\n')
        sleep(5)

    def __start_backup(self):
        info("*** Disaster was predicted and start emergency backup!\n")
        network_name = self.__network_name()
        self.__sender.cmd(f"./bin/{network_name}/client -addr {self.__receiver.IP()}:44300 -chunk 1G.txt "
                          f"> log/client_{network_name}.log 2>&1 &")

    def __network_name(self) -> str:
        return self.__network.name.lower()
