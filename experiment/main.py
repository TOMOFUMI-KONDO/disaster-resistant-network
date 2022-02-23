from argparse import Namespace, ArgumentParser

from mininet.log import setLogLevel

from enums import Network
from experiment import Experiment


def main():
    args = parse()
    setLogLevel(args.log)

    for n in [Network.TCP, Network.QUIC]:
        experiment = Experiment(n, {
            'user': args.dbuser,
            'pass': args.dbpass,
            'host': args.dbhost,
            'port': args.dbport,
            'database': args.dbdb,
        })
        experiment.run()


def parse() -> Namespace:
    parser = ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    parser.add_argument("--dbuser", dest="dbuser", type=str, default="root", help="database user")
    parser.add_argument("--dbpass", dest="dbpass", type=str, default="", help="database pass")
    parser.add_argument("--dbhost", dest="dbhost", type=str, default="127.0.0.1", help="database host")
    parser.add_argument("--dbport", dest="dbport", type=int, default="3306", help="database port")
    parser.add_argument("--dbdb", dest="dbdb", type=str, default="", help="database name")
    return parser.parse_args()


if __name__ == "__main__":
    main()
