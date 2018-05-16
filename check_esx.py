#! /usr/bin/python3

from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL, Disconnect
import argparse
import atexit
import sys

def validate_options():
    parser = argparse.ArgumentParser(description='Input parameters',formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--critical',dest='crit',default='90',
                         help='Set the critical threshold')
    parser.add_argument('-w', '--warning',dest='warn',default='80',
                         help='Set the warning threshold')
    parser.add_argument('-l', '--command',dest='cmd',
                         help='Specify command type (cpu, mem, service)')
    parser.add_argument('-s', '--subcommand',dest='sub',
                         help='Specify subcommand')
    parser.add_argument('-t', '--timeout',dest='timeout',default=30,
                         help='Seconds before plugin times out')
    parser.add_argument('-H', '--host',dest='host',
                         help='ESXi hostname.')
    parser.add_argument('-f', '--authfile',dest='auth',
                         help='''Authentication file with login and password. File syntax:
username=<login>
password=<password>''')
    args=parser.parse_args()
    if (args.host == None):
        parser.error('Missing hostname.')
    if (args.auth == None):
        parser.error('Missing authfile.')
    if (args.cmd not in ['cpu', 'mem', 'service']):
        parser.error('Missing or invalid command.')
    if (args.cmd == 'service') and (args.sub not in ['ntpd']):
        parser.error('Missing or invalid subcommand.')
    return args

def main():
    opts=validate_options()
    login=None
    password=None
    with open(opts.auth,"r") as authfile:
        for line in authfile:
            line_parsed=[x.strip() for x in line.split('=')]
            if(line_parsed[0] == 'username'):
                login=line_parsed[1]
            if(line_parsed[0] == 'password'):
                password=line_parsed[1]
    if (login == None) or (password == None):
        print ('Authfile missing username or password.')
        sys.exit(2)
    si=SmartConnectNoSSL(host=opts.host, port=443, user=login, pwd=password,connectionPoolTimeout=opts.timeout)
    atexit.register(Disconnect, si)
    content=si.RetrieveContent()
    hostid=si.content.rootFolder.childEntity[0].hostFolder.childEntity[0].host[0]
    if (opts.cmd == 'cpu') or (opts.cmd == 'mem'):
        stats=hostid.summary.quickStats
        hardware=hostid.summary.hardware
        if (opts.cmd == 'cpu'):
            usage=(stats.overallCpuUsage / (hardware.numCpuCores * hardware.cpuMhz) * 100)
        if (opts.cmd == 'mem'):
            usage=(stats.overallMemoryUsage / (hardware.memorySize / 1024 / 1024) * 100)
        if (usage > float(opts.crit)):
            print ("CRITICAL - %s usage=%f" % (opts.cmd,usage))
            sys.exit(2)
        elif (usage > float(opts.warn)):
            print ("WARNING - %s usage=%f" % (opts.cmd,usage))
            sys.exit(1)
        else:
            print ("OK - %s usage=%f" % (opts.cmd,usage))
            sys.exit(0)
    elif (opts.cmd == 'service'):
        service=hostid.configManager.serviceSystem
        for item in service.serviceInfo.service:
            if item.key == 'ntpd':
                if item.running:
                    print ('OK - All services are in their apropriate state.')
                    sys.exit(0)
                else:
                    print ("CRITICAL - %s is down" % (item.key))
                    sys.exit(2)

if __name__ == '__main__':
    main()
