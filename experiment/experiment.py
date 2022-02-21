from __future__ import annotations

from time import sleep

import requests
from mininet.log import info, error
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from disaster_scheduler import DisasterScheduler, LinkFailure, HostFailure
from enums import Network


class Experiment(object):
    def __init__(self, network: Network):
        self.__network = network

        self.__net = Mininet(
            topo=DisasterResistantNetworkTopo(),
            controller=RemoteController("c0", port=6633),
        )
        hosts = self.__net.hosts
        self.__host_pairs = [
            {'client': hosts[0], 'server': hosts[1], 'chunk': 10 ** 10 * 2},
            {'client': hosts[2], 'server': hosts[3], 'chunk': 10 ** 11},
        ]

        self.__disaster_scheduler = DisasterScheduler(
            self.__net.switches,
            {'h1c': hosts[0], 'h1s': hosts[1], 'h2c': hosts[2], 'h2s': hosts[3]}
        )

    def run(self):
        self.__net.start()
        self.__prepare_backup()

        # assume that a disaster was predicted
        pids = self.__start_backup()
        self.__disaster_scheduler.run([
            LinkFailure("s2", 2, "s4", 1, 100),
            HostFailure("h1c", pids[0], 220),
            HostFailure("h2c", pids[1], 400),
        ])

        # wait until disaster finishes
        sleep(450)

        self.__net.stop()
        self.__init_controller()

        # cleanup time
        sleep(10)

    def __prepare_backup(self):
        network_name = self.__network_name()
        for hp in self.__host_pairs:
            server = hp['server']
            server.cmd(f"./bin/{network_name}/server -v > log/{network_name}/{server.name}.log 2>&1 &")

        info('*** waiting to boot server...\n')
        sleep(10)

    def __start_backup(self) -> list[int]:
        info("*** Disaster was predicted and start emergency backup!\n")

        pids = []
        network_name = self.__network_name()
        for hp in self.__host_pairs:
            client = hp['client']
            server = hp['server']
            chunk = hp['chunk']
            client.cmd(f"./bin/{network_name}/client -addr {server.IP()}:44300 -chunk {chunk} "
                       f"> log/{network_name}/{client.name}.log 2>&1 &")
            pids.append(int(client.cmd("echo $!")))

        # notify start of a disaster
        r = requests.post('http://localhost:8080/disaster')
        if r.status_code != 200:
            error("failed to notify disaster to controller: %d %s", r.status_code, r.text)

        return pids

    def __init_controller(self):
        r = requests.put('http://localhost:8080/init')
        if r.status_code != 200:
            error("failed to initialize controller: %d %s", r.status_code, r.text)

    def __network_name(self) -> str:
        return self.__network.name.lower()
