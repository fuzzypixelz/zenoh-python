#
# Copyright (c) 2023 ZettaScale Technology
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0, or the Apache License, Version 2.0
# which is available at https://www.apache.org/licenses/LICENSE-2.0.
#
# SPDX-License-Identifier: EPL-2.0 OR Apache-2.0
#
# Contributors:
#   ZettaScale Zenoh Team, <zenoh@zettascale.tech>
#

import argparse
import json
import time
import zenoh
import sys

# --- Command line argument parsing --- --- --- --- --- ---
parser = argparse.ArgumentParser(
    prog='z_ping',
    description='zenoh ping example')
parser.add_argument('--mode', '-m', dest='mode',
                    choices=['peer', 'client'],
                    type=str,
                    help='The zenoh session mode.')
parser.add_argument('--connect', '-e', dest='connect',
                    metavar='ENDPOINT',
                    action='append',
                    type=str,
                    help='Endpoints to connect to.')
parser.add_argument('--listen', '-l', dest='listen',
                    metavar='ENDPOINT',
                    action='append',
                    type=str,
                    help='Endpoints to listen on.')
parser.add_argument('--prefix', '-p', dest='prefix',
                    default='demo/example/zenoh-python',
                    type=str,
                    help='The key expression to prefix the pub/sub key expressions.')
# TODO: --no-multicast-scouting, --enable-shm
parser.add_argument('--config', '-c', dest='config',
                    metavar='FILE',
                    type=str,
                    help='A configuration file.')

args = parser.parse_args()
conf = zenoh.Config.from_file(
    args.config) if args.config is not None else zenoh.Config()
if args.mode is not None:
    conf.insert_json5(zenoh.config.MODE_KEY, json.dumps(args.mode))
if args.connect is not None:
    conf.insert_json5(zenoh.config.CONNECT_KEY, json.dumps(args.connect))
if args.listen is not None:
    conf.insert_json5(zenoh.config.LISTEN_KEY, json.dumps(args.listen))

# Zenoh code  --- --- --- --- --- --- --- --- --- --- ---

# initiate logging
zenoh.init_logger()

print("Opening session...")
session = zenoh.open(conf)

pub = session.declare_publisher(
    f"{args.prefix}/pong", 
    congestion_control=zenoh.CongestionControl.BLOCK()
)
sub = session.declare_subscriber(
    f"{args.prefix}/ping",
    handler=lambda value: pub.put(value.payload)
)

session.close()
