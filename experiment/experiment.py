from __future__ import annotations

import json
import random
from time import sleep
from typing import Optional

import requests
from mininet.log import info, error
from mininet.net import Mininet
from mininet.node import RemoteController
from mysql import connector

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from disaster_scheduler import DisasterScheduler, LinkFailure, HostFailure
from enums import Network


class Experiment(object):
    __URL = "http://localhost:8080"

    def __init__(self, network: Network, size: int, db_config: dict):
        self.__network = network
        self.__db_config = db_config

        self.__net = Mininet(
            topo=DisasterResistantNetworkTopo(size=size),
            controller=RemoteController("c0", port=6633),
        )
        hosts = self.__net.hosts

        self.__host_pairs = [
            {'client': hosts[0], 'server': hosts[1], 'chunk': 10 ** 10 * 2},  # 20GB
            {'client': hosts[2], 'server': hosts[3], 'chunk': 10 ** 10 * 5},  # 50GB
            {'client': hosts[4], 'server': hosts[5], 'chunk': 10 ** 11},  # 100GB
        ]

        self.__disaster_scheduler = DisasterScheduler(
            self.__net.switches,
            {"h1c": hosts[0], "h1s": hosts[1], "h2c": hosts[2], "h2s": hosts[3], "h3c": hosts[4], "h3s": hosts[5]}
        )

    def run(self):
        try:
            exp_id = self.__record()
            info(f"*** experiment {exp_id} started!\n")

            self.__net.start()
            sleep(10)  # wait controller to receive switch feature message

            topo: DisasterResistantNetworkTopo = self.__net.topo
            topo.register_links()
            topo.register_host_pairs()

            self.__prepare_backup(exp_id)

            # assume that a disaster was predicted
            pids = self.__start_backup()

            link_failures = [
                LinkFailure("s4", 2, "s5", 1, self.__rand_link_fail_time()),
                LinkFailure("s8", 3, "s9", 2, self.__rand_link_fail_time()),
                LinkFailure("s9", 4, "s14", 1, self.__rand_link_fail_time()),
                LinkFailure("s10", 3, "s15", 1, self.__rand_link_fail_time()),
                LinkFailure("s13", 3, "s14", 2, self.__rand_link_fail_time()),
                LinkFailure("s13", 4, "s18", 1, self.__rand_link_fail_time()),
                LinkFailure("s15", 3, "s20", 1, self.__rand_link_fail_time()),
                LinkFailure("s19", 3, "s20", 2, self.__rand_link_fail_time()),
                LinkFailure("s20", 3, "s25", 1, self.__rand_link_fail_time()),
                LinkFailure("s23", 3, "s24", 2, self.__rand_link_fail_time()),
            ]
            host_failures = [
                HostFailure("h1c", pids[0], 300),
                HostFailure("h2c", pids[1], 450),
                HostFailure("h3c", pids[2], 600),
            ]
            self.__register_disaster_info(link_failures, host_failures)
            self.__disaster_scheduler.run([*link_failures, *host_failures])

            # wait until disaster finishes
            sleep(660)
        finally:
            self.__net.stop()
            self.__init_controller()

        # cleanup time
        sleep(60)

    def __record(self) -> int:
        conn = connector.connect(
            user=self.__db_config['user'],
            password=self.__db_config['pass'],
            host=self.__db_config['host'],
            port=self.__db_config['port'],
            database=self.__db_config['database']
        )
        cursor = conn.cursor()

        cursor.execute("INSERT INTO experiments (network_id) SELECT id FROM networks WHERE name = %s",
                       [self.__network.name_lower])
        exp_id = cursor.lastrowid
        for hp in self.__host_pairs:
            client = hp['client']
            server = hp['server']
            chunk = hp['chunk']
            cursor.execute("INSERT INTO backup_pairs (experiment_id, name, data_size_byte) VALUES(%s, %s, %s)",
                           [exp_id, f"{client}-{server}", chunk])

        conn.commit()
        cursor.close()
        conn.close()

        return exp_id

    def __prepare_backup(self, exp_id: int):
        net = self.__network.name_lower
        for hp in self.__host_pairs:
            client = hp['client']
            server = hp['server']
            cfg = self.__db_config
            server.cmd(f"./bin/{net}/server -v -exp={exp_id} -pair={client}-{server} -dbuser={cfg['user']} "
                       f"-dbpass={cfg['pass']} -dbhost={cfg['host']} -dbport={cfg['port']} -dbdb={cfg['database']} "
                       f"> log/{net}/{server.name}.log 2>&1 &")

        info('*** waiting to boot server...\n')
        sleep(30)

    def __start_backup(self) -> list[int]:
        info("*** Disaster was predicted and start emergency backup!\n")

        # notify start of a disaster
        r = requests.post('http://localhost:8080/disaster')
        if r.status_code != 200:
            error("failed to notify disaster to controller: %d %s", r.status_code, r.text)

        pids = []
        net = self.__network.name_lower
        for hp in self.__host_pairs:
            client = hp['client']
            server = hp['server']
            chunk = hp['chunk']
            client.cmd(f"./bin/{net}/client -addr {server.IP()}:44300 -chunk {chunk} "
                       f"> log/{net}/{client.name}.log 2>&1 &")

            pids.append(int(client.cmd("echo $!")))

        return pids

    def __register_disaster_info(self, link_failures: list[LinkFailure], host_failures: list[HostFailure]):
        for l in link_failures:
            requests.put(self.__URL + "/link", data=json.dumps({
                "switch1": l.switch1,
                "switch2": l.switch2,
                "fail_at_sec": l.fail_at_sec,
            }))

        for h in host_failures:
            host_pair = self.__find_host_pair_by_client(h.host)
            if host_pair is None:
                raise Exception(f"host pair whose client is {h.host} was not found.")

            requests.put(self.__URL + "/host-client", data=json.dumps({
                "client": h.host,
                "fail_at_sec": h.fail_at_sec,
                "datasize_gb": host_pair["chunk"],
            }))

    def __find_host_pair_by_client(self, client: str) -> Optional[dict]:
        for h in self.__host_pairs:
            if h["client"].name == client:
                return h

    def __init_controller(self):
        r = requests.put(self.__URL + "/init")
        if r.status_code != 200:
            error("failed to initialize controller: %d %s", r.status_code, r.text)

    def __rand_link_fail_time(self) -> int:
        return random.randint(60, 600)
