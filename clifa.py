#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyefa import networks
import argparse, sys, datetime, json, os, subprocess, re

def parse_point(desc, myparser):
	if type(desc) == str: desc = [desc]
	if len(desc) == 1:
		try: 
			data = json.load(open(os.path.expanduser('~/.clifa/aliases.json'), 'r'))
		except:
			data = {}
		
		if desc[0] not in data:
			myparser.error('Unknown alias "%s"' % desc[0])
		try:
			desc = [a.encode('utf8') for a in data[desc[0]]]
		except:
			desc = data[desc[0]]
		
	if len(desc) == 2:
		if desc[1].startswith('addr:'):
			if '' in (desc[0], desc[1][5:]):
				myparser.error('Invalid point description %s' % repr(' '.join(desc)))
			return [desc[0], desc[1][5:], 'address']
		elif desc[1].startswith('poi:'):
			if '' in (desc[0], desc[1][4:]):
				myparser.error('Invalid point description %s' % repr(' '.join(desc)))
			return [desc[0], desc[1][4:], 'poi']
		else:
			if '' in desc:
				myparser.error('Invalid point description %s' % repr(' '.join(desc)))
			return desc + ['stop']
	else:
		myparser.error('Invalid point description %s' % repr(' '.join(desc)))
		
def getwifi():
	# Alle WLANe scannen und nebenbei devices erfahren
	p = subprocess.Popen(['iw', 'dev'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	data = p.communicate()[0].split('\n')
	
	devices = []
	for line in data:
		if line.strip().startswith('Interface'):
			devices.append(line.split('Interface')[1].strip())
	
	aps = []		
	for device in devices:
		p = subprocess.Popen(['iw', 'dev', device, 'link'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		data = p.communicate()[0]
		
		if 'SSID:' in data:
			match = re.findall('([0-9abcdef]{2}(:[0-9abcdef]{2}){5})', data, re.MULTILINE)
			if match:
				aps.append([match[0][0], data.split('SSID:')[1].strip().split('\n')[0].split(' ')[0]])
	
	return aps
	
def wifimatch():
	try: 
		data = json.load(open(os.path.expanduser('~/.clifa/wifi.json'), 'r'))
	except:
		data = {}
		
	wifis = getwifi()
	matches = []
	for wifi in wifis:
		for line in data:
			if (line['mac'] is None or line['mac'] == wifi[0]) and (line['ssid'] is None or line['ssid'] == wifi[1]):
				matches.append(line)
	
	return matches
		
def oneword(desc):
	return ('"%s"' % desc) if ' ' in desc else desc
	
parser = argparse.ArgumentParser(prog='clifa', description='Inofficial Client vor EFA-Backends')        
parser.add_argument('-N', '--network', metavar='network', help='Network to use. Currently supported: %s'%', '.join(networks.supported), choices=networks.supported, default='vrr')
parser.add_argument('-a', '--api', metavar='xml|json|both', choices=('xml', 'json', 'both'), help='API to use. For maximum information, use both (default). XML and JSON may have information missing but may be faster, as they need only one request.', default='both')
subparsers = parser.add_subparsers(dest='subparser', title='commands')

# ROUTE
usage_route = """
       route [options] from-city from-stop [via-city via-stop] to-city to-stop
       route [options] from-city from-stop [via-city via-stop] to-alias
       route [options] [to-city to-stop | to-alias]
       route [ --from city place ] --to city place [ options ]
""".strip()
parser_route = subparsers.add_parser('route', usage=usage_route, help='Connection Search')
parser_route.add_argument('--from', dest='frm', nargs='+', metavar='frm', help='Departure place', default=None)
parser_route.add_argument('--to', nargs='+', metavar='to', help='Arrival place')
parser_route.add_argument('--via', nargs='+', metavar='via', help='Travel via this place')

station_help = """
  Origin, Destination and via can be set via short or long syntax.
  You can use two to describe city and stop or one to access a saved point by alias.
  Please note that in the short syntax, alias access is only supported for destination.
  In case you want stop to be an address or "point of interest", you can set it to 'addr:something' or 'poi:something'.
  If origin is ommited, clifa will try to obtain your location.  
""".strip()
parser_route.add_argument('stations', nargs='*', metavar='route description', help=station_help)
parser_route.add_argument('-t', '--time', metavar='hh:ii', help='Journey time (if ommitted: now)')
parser_route.add_argument('-d', '--date', metavar='dd.mm.[yyyy]', help='Journey time (if ommitted: now)')

parse_route_time_group = parser_route.add_mutually_exclusive_group(required=False)
parse_route_time_group.add_argument('-A', '--arrival', help='Treat Jorney time as arrival time', action='store_const', dest='timetype', const='arr')
parse_route_time_group.add_argument('-T', '--departure', help='Treat Jorney time as departure time (default)', action='store_const', dest='timetype', const='dep')

parser_route.add_argument('-b', '--bike', help='Choose connections allowing to carry a bike', action='store_const', const=True, default=False)
parser_route.add_argument('-e', '--exclude', metavar='exclude', help='Exclude transports (comma separated list).\n\nPossible transports: zug, s-bahn, u-bahn, stadtbahn, tram, stadtbus, regionalbus, schnellbus, seilbahn, schiff, ast, sonstige', default=None)

parser_route.add_argument('-m', '--max-change', metavar='number', help='Print connections with at most number interchanges', type=int, default=None)
parser_route.add_argument('-P', '--prefer', metavar='speed | nowait | nowalk', choices=('speed', 'nowait', 'nowalk'), help='Prefered connection type (default: speed)', default='speed')

parser_route.add_argument('-p', '--proximity', help='Take stops close to the stop/start into account and possibly use them instead', action='store_const', const=True, default=False)
parser_route.add_argument('-i', '--include', metavar='local | ic | ice', choices=('local', 'ic', 'ice'), help='Highest allowed train type (default: local)', default='local')
parser_route.add_argument('-w', '--walk-speed', metavar='slow | normal | fast', choices=('slow', 'normal', 'fast'), help='Walking speed (default: normal)', default='normal')

# ALIAS
usage_alias = """
       alias list
       alias add alias city stop
       alias delete alias
""".strip()
parser_alias = subparsers.add_parser('alias', usage=usage_alias, help='Configure location aliases')
parser_alias.add_argument('command', nargs=1, help=argparse.SUPPRESS, choices=('list', 'add', 'delete'))
parser_alias.add_argument('alias', nargs='?', help='Alias name. Case sensitive.')
parser_alias.add_argument('city', nargs='?', help='City name')
parser_alias.add_argument('stop', nargs='?', help="""Stop name. In case you want stop to be an address or "point of interest", you can set it to 'addr:something' or 'poi:something'.""")

# WIFI
usage_wifi = """
       wifi list
       wifi add [ -s ssid ] [ -m mac ] city stop
       wifi current
       wifi delete [ -s ssid ] [ -m mac ]
""".strip()
parser_wifi = subparsers.add_parser('wifi', usage=usage_wifi, help='Configure locating by wifi recognition')
parser_wifi.add_argument('command', nargs=1, help=argparse.SUPPRESS, choices=('list', 'add', 'current', 'delete'))
parser_wifi.add_argument('city', nargs='?', help='City name')
parser_wifi.add_argument('stop', nargs='?', help="""Stop name. In case you want stop to be an address or "point of interest", you can set it to 'addr:something' or 'poi:something'.""")
parser_wifi.add_argument('-s', '--ssid', help='SSID of the WiFi. If ommited, no SSID matching will occur.')
parser_wifi.add_argument('-m', '--mac', help='Mac-Adress of the WiFi. If ommited, no Mac matching will occur.\n\nIf both are omitted, mac and ssid of the wifi currently connected to will be used.')

# WEITERE PARSER
parser_route = subparsers.add_parser('departures', usage=usage_route, help='List departures at specific Point')
parser_route = subparsers.add_parser('search', usage=usage_route, help='Search for stations')
parser_route = subparsers.add_parser('network', usage=usage_route, help='Set default network')
parser_route = subparsers.add_parser('set', usage=usage_route, help='Manage default route options')

args = parser.parse_args()

# NETWORK
efa = networks.network(args.network)
	
mots = ['zug', 's-bahn', 'u-bahn', 'stadtbahn', 'tram', 'stadtbus', 'regionalbus', 'schnellbus', 'seilbahn', 'schiff', 'ast', 'sonstige']

if args.subparser == 'route':
	point_from = None
	point_to   = None
	point_via  = None
	if len(args.stations) > 6:
		parser_route.error('not a valid route description')
	
	if len(args.stations) in [1, 2]: point_to = args.stations
	if len(args.stations) > 2:       point_from = args.stations[0:2]
	if len(args.stations) == 3:      point_to = args.stations[2]
	if len(args.stations) in [4, 5]: point_to = args.stations[2:4]
	if len(args.stations) == 5:      point_via = args.stations[4]
	if len(args.stations) == 6:
		point_via = args.stations[2:4]
		point_to  = args.stations[4:6]
		
	if args.frm is not None: point_from = args.frm
	if args.via is not None: point_via  = args.via
	if args.to  is not None: point_to   = args.to
			
	if point_from is not None: point_from = parse_point(point_from, parser_route)
	if point_via  is not None: point_via  = parse_point(point_via, parser_route)
	if point_to   is not None: point_to   = parse_point(point_to, parser_route)
	
	if point_to is None:
		parser_route.error('no destination given')
		sys.exit(1)
	if point_from is None:
		wifis = wifimatch()
		if not wifis:
			print 'no origin given and obtaining location by wifi failed'
			sys.exit(1)
		point_from = parse_point([wifis[0]['city'].encode('utf8'), wifis[0]['stop'].encode('utf8')], parser_route)
	
	now = datetime.datetime.now()
	if args.time is None:
		time = [now.hour, now.minute]
	elif re.match('^[0-9]{2}:[0-9]{2}$', args.time):
		time = [int(i) for i in args.time.split(':')]
	else:
		parser_route.error('invalid time format')
		sys.exit(1)
		
	if args.date is None:
		date = [now.day, now.month, now.year]
	elif re.match('^[0-9]{2}.[0-9]{2}.[0-9]{4}$', args.time):
		date = [int(i) for i in args.time.split('.')]
	elif re.match('^[0-9]{2}.[0-9]{2}.$', args.time):
		date = [int(i) for i in args.time[0:-1].split('.')] + [now.year]
	else:
		parser_route.error('invalid date format')
		sys.exit(1)	
		
	time = datetime.datetime(date[2], date[1], date[0], time[0], time[1])
	timetype = 'dep' if args.timetype is None else args.timetype
	
	if args.max_change is None:
		max_interchanges = 9
	elif args.max_change < 0:
		parser_route.error('max. interchanges needs to be >= 0')
		sys.exit(1)	
	else:
		max_interchanges = args.max_change
		
	if args.exclude is not None:
		exclude = args.exclude.split(',')
		wrongs = list(set(exclude)-set(mots))
		if len(wrongs) > 0:
			parser_route.error('invalid mots in exclude')
			sys.exit(1)	
	else:
		exclude = []
	
	if sys.stdout.isatty():
		sys.stdout = os.popen('less -R', 'w')
	print efa.tripRequest(origin=point_from, destination=point_to, via=point_via, time=time, timetype=timetype, max_interchanges=max_interchanges, select_interchange_by=args.prefer, use_near_stops=args.proximity, train_type=args.include, walk_speed=args.walk_speed, with_bike=args.bike, apitype=args.api)
	
	
elif args.subparser == 'alias':
	try: 
		data = json.load(open(os.path.expanduser('~/.clifa/aliases.json'), 'r'))
	except:
		data = {}
		
	cmd = args.command[0]
	if cmd == 'list':
		if args.alias is not None: 
			parser_alias.error('too many arguments')
			
		print '%d aliases' % len(data)
		for k, v in data.iteritems():
			print '%s: %s %s' % (oneword(k), oneword(v[0]), oneword(v[1]))
	elif cmd == 'add':
		if args.stop is None: 
			parser_alias.error('too few arguments')
			
		# Wirft nen fehler wenns invalide ist
		test = parse_point([args.city, args.stop], parser_alias)
		
		data[args.alias] = [args.city, args.stop]
		
		try: 
			os.mkdir(os.path.expanduser('~/.clifa'))
		except:
			pass
		json.dump(data, open(os.path.expanduser('~/.clifa/aliases.json'), 'w'))
		
	elif cmd == 'delete':
		if args.alias is None:
			parser_alias.error('too fed arguments')
		if args.city is not None: 
			parser_alias.error('too many arguments')
			
		if args.alias in data: del data[args.alias]
		
		try: 
			os.mkdir(os.path.expanduser('~/.clifa'))
		except:
			pass
		json.dump(data, open(os.path.expanduser('~/.clifa/aliases.json'), 'w'))
		
		
elif args.subparser == 'wifi':
	try: 
		data = json.load(open(os.path.expanduser('~/.clifa/wifi.json'), 'r'))
	except:
		data = []
		
	cmd = args.command[0]
	if cmd == 'list':
		if args.city is not None: 
			parser_alias.error('too many arguments')
			
		print '%d known wifi' % len(data)
		for item in data:
			print 'MAC:%s SSID:%s %s %s' % (oneword(item['mac']), oneword(item['ssid']), oneword(item['city']), oneword(item['stop']))
	elif cmd == 'add' or cmd == 'delete':
		if cmd == 'add' and args.stop is None: 
			parser_alias.error('too few arguments')
		if cmd == 'delete' and args.city is not None: 
			parser_alias.error('too many arguments')
			
		if args.ssid is None and args.mac is None:
			wifis = getwifi()
			if not wifis:
				print 'No WiFi-Properties were given and no wifi connection was found.'
				sys.exit(1)
			wifi = {'mac': wifis[0][0], 'ssid': wifis[0][1]}
		else:
			wifi = {'mac': args.mac, 'ssid': args.ssid}
		
		if cmd == 'add':	
			# Wirft nen fehler wenns invalide ist
			test = parse_point([args.city, args.stop], parser_alias)
			wifi['city'] = args.city
			wifi['stop'] = args.stop
		
		# Gleiche einträge entfernen
		olddata = data
		data = []
		for w in olddata:
			if wifi['mac'] != w['mac'] or wifi['ssid'] != w['ssid']:
				wifi.append(w)
		
		if cmd == 'add':
			data.append(wifi)
		
		try: 
			os.mkdir(os.path.expanduser('~/.clifa'))
		except:
			pass
		json.dump(data, open(os.path.expanduser('~/.clifa/wifi.json'), 'w'))
	elif cmd == 'current':
		if args.city is not None: 
			parser_alias.error('too many arguments')
			
		wifis = getwifi()
		print 'currently connected to %d wifi' % len(wifis)
		for wifi in wifis:
			print 'MAC:%s SSID:%s' % (wifi[0], wifi[1])
			
		matches = wifimatch()
		print '\n%d Matches: (first match will be used)' % len(matches)
		
		for item in matches:
			print 'MAC:%s SSID:%s %s %s' % (oneword(item['mac']), oneword(item['ssid']), oneword(item['city']), oneword(item['stop']))
	
else:
	print 'Not yet supported'
	sys.exit(1)
