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
import logging
import sys
import time
import zenoh

# logging.basicConfig(level=logging.DEBUG)

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
parser.add_argument('--samples', '-n', dest='samples',
                    metavar='N',
                    default=100,
                    type=int,
                    help='The number of round-trips to measure.')
parser.add_argument('--warmup', '-w', dest='warmup',
                    metavar='W',
                    default=50,
                    type=int,
                    help='The number round-trip measurements to warm up.')
# TODO: --no-multicast-scouting, --enable-shm
parser.add_argument('--config', '-c', dest='config',
                    metavar='FILE',
                    type=str,
                    help='A configuration file.')
parser.add_argument(dest='size',
                    metavar='S',
                    type=int,
                    help='Payload size in bytes.')

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

value = bytes(i % 10 for i in range(args.size))
samples = [] # RTTs in micro seconds
clock = None # time counter in nano seconds
seq = 0
_condvar = False

def ping(_):
    global value, samples, clock, seq, pub, sub, _condvar
    elapsed = (time.perf_counter_ns() - clock) / 1000
    samples.append(elapsed)
    
    if seq < (args.warmup + args.samples):
        logging.info(f"seq: {seq}, size: {len(value)}B, round-trip time: {elapsed}µs, latency: {elapsed / 2}µs")

        if seq == args.warmup:
            logging.info(f"collected {len(samples)} warmup samples in {args.warmup}s")
            samples.clear()

        seq += 1
        clock = time.perf_counter_ns()
        pub.put(value)
    else:
        rtt = sum(samples) / len(samples)
        print(f"payload size:            {len(value)}")
        print(f"samples count:           {len(samples)}")
        print(f"average round-trip time: {round(rtt, 2)}µs")
        print(f"average latency:         {round(rtt / 2, 2)}µs")
        _condvar = True

pub = session.declare_publisher(
    f"{args.prefix}/ping", 
    congestion_control=zenoh.CongestionControl.BLOCK()
)
sub = session.declare_subscriber(f"{args.prefix}/pong", ping)

# Entrypoint
clock = time.perf_counter_ns()
pub.put(value)

# NOTE: If we undeclare sub in `ping`, it tries to join its own thread and pyo3 panics;
# the `condvar` signals to the main thread that it's safe to close the session.
while not _condvar:
    time.sleep(1)

sub.undeclare()
pub.undeclare()
session.close()