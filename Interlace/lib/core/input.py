from argparse import ArgumentParser
from netaddr import IPNetwork, IPRange, IPGlob
from Interlace.lib.core.output import OutputHelper, Level
import os.path


class InputHelper(object):
    @staticmethod
    def readable_file(parser, arg):
        if not os.path.exists(arg):
            parser.error("The file %s does not exist!" % arg)
        else:
            return open(arg, 'r')  # return an open file handle

    @staticmethod
    def check_positive(parser, arg):
        ivalue = int(arg)
        if ivalue <= 0:
            raise parser.ArgumentTypeError("%s is not a valid positive integer!" % arg)

        return arg

    @staticmethod
    def _get_ips_from_range(ip_range):
        ips = set()
        ip_range = ip_range.split("-")

        # parsing the above structure into an array and then making into an IP address with the end value
        end_ip = ".".join(ip_range[0].split(".")[0:-1]) + "." + ip_range[1]

        # creating an IPRange object to get all IPs in between
        range_obj = IPRange(ip_range[0], end_ip)

        for ip in range_obj:
            ips.add(str(ip))

        return ips

    @staticmethod
    def _get_ips_from_glob(glob_ips):
        ip_glob = IPGlob(glob_ips)

        ips = set()

        for ip in ip_glob:
            ips.add(str(ip))

        return ips

    @staticmethod
    def _get_cidr_to_ips(cidr_range):
        ips = set()

        for ip in IPNetwork(cidr_range):
            ips.add(str(ip))

        return ips

    @staticmethod
    def process_commands(arguments):
        commands = set()
        ranges = set()
        targets = set()
        final_commands = set()
        output = OutputHelper(arguments)

        ports = arguments.port.split(",")

        # process targets first
        if arguments.target:
            ranges.add(arguments.target)
        else:
            for target in arguments.target_list:
                ranges.add(target.strip())

        # removing elements that may have spaces (helpful for easily processing comma notation)
        for target in ranges:
            target = target.replace(" ", "")

            for ips in target.split(","):
                # checking for CIDR
                if not arguments.nocidr and "/" in ips:
                    targets.update(InputHelper._get_cidr_to_ips(ips))
                # checking for IPs in a range 
                elif "-" in ips:
                    targets.update(InputHelper._get_ips_from_range(ips))
                # checking for glob ranges
                elif "*" in ips:
                    targets.update(InputHelper._get_ips_from_glob(ips))
                else:
                    targets.add(ips)

        if arguments.command:
            commands.add(arguments.command)
        else:
            for command in arguments.command_list:
                commands.add(command.strip())

        # expand commands to all known targets
        for target in targets:
            # replace flags
            for command in commands:
                tmp_command = command
                for port in ports:
                    command = tmp_command
                    command = str(command).replace("_target_", target)
                    command = str(command).replace("_host_", target)
                    if arguments.output:
                        command = str(command).replace("_output_", arguments.output)
                    if arguments.port:
                        command = str(command).replace("_port_", port)
                    if arguments.realport:
                        command = str(command).replace("_realport_", arguments.realport)
                    final_commands.add(command)
                    output.terminal(Level.VERBOSE, command, "Added after processing")

        return final_commands


class InputParser(object):
    def __init__(self):
        self._parser = self.setup_parser()

    def parse(self, argv):
        return self._parser.parse_args(argv)

    @staticmethod
    def setup_parser():
        parser = ArgumentParser()

        targets = parser.add_mutually_exclusive_group(required=True)

        targets.add_argument(
            '-t', dest='target', required=False,
            help='Specify a target or domain name either in comma format, '
                 'CIDR notation, or a single target.'
        )

        targets.add_argument(
            '-tL', dest='target_list', required=False,
            help='Specify a list of targets or domain names.',
            metavar="FILE",
            type=lambda x: InputHelper.readable_file(parser, x)
        )

        parser.add_argument(
            '-threads', dest='threads', required=False,
            help="Specify the maximum number of threads to run (DEFAULT:5)",
            default=5,
            type=lambda x: InputHelper.check_positive(parser, x)
        )

        parser.add_argument(
            '-timeout', dest='timeout', required=False,
            help="Command timeout in seconds (DEFAULT:600)",
            default=600,
            type=lambda x: InputHelper.check_positive(parser, x)
        )

        commands = parser.add_mutually_exclusive_group(required=True)
        commands.add_argument(
            '-c', dest='command',
            help='Specify a single command to execute.'
        )

        commands.add_argument(
            '-cL', dest='command_list', required=False,
            help='Specify a list of commands to execute',
            metavar="FILE",
            type=lambda x: InputHelper.readable_file(parser, x)
        )

        parser.add_argument(
            '-o', dest='output',
            help='Specify an output folder variable that can be used in commands as _output_'
        )

        parser.add_argument(
            '-p', dest='port',
            help='Specify a port variable that can be used in commands as _port_'
        )

        parser.add_argument(
            '-rp', dest='realport',
            help='Specify a real port variable that can be used in commands as _realport_'
        )

        parser.add_argument(
            '--no-cidr', dest='nocidr', action='store_true', default=False,
            help='If set then CIDR notation in a target file will not be automatically '
                 'be expanded into individual hosts.'
        )

        parser.add_argument(
            '--no-color', dest='nocolor', action='store_true', default=False,
            help='If set then any foreground or background colours will be '
                 'stripped out.'
        )

        output_types = parser.add_mutually_exclusive_group()
        output_types.add_argument(
            '-v', '--verbose', dest='verbose', action='store_true', default=False,
            help='If set then verbose output will be displayed in the terminal.'
        )
        output_types.add_argument(
            '--silent', dest='silent', action='store_true', default=False,
            help='If set only findings will be displayed and banners '
                 'and other information will be redacted.'
        )

        return parser
