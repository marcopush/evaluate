#!/usr/bin/env python3

import os
import sys
import argparse
import itertools as it
import collections as cl

import flock
import alist
import config

def iter_values (defaults, tests):
    unique = {}

    for key, val in defaults.items():
        unique[key] = { val }
        yield key, val

    for test in tests:
        for key, vals in test:
            for val in vals:
                if val not in unique[key]:
                    yield key, val

def iter_params (defaults, tests):
    unique = set()

    for key, val in defaults.items():
        unique.add(key)
        yield key, [ val ]

    for test in tests:
        for key, vals in test:
            if key not in unique:
                yield key, vals
                unique.add(key)

def iter_tests (defaults, tests, order):
    key = lambda x: order[x[0]]

    for test in tests:
        keys = [ key for key, _ in test ]
        opts = [ opt for _, opt in test ]

        for vals in it.product(*opts):
            flags = { **defaults, **dict(zip(keys, vals)) }
            flags = cl.OrderedDict(sorted(flags.items(), key = key))

            if config.ignore(flags):
                continue

            yield tuple(flags.items())

argparser = argparse.ArgumentParser()
argparser.add_argument("-clear", action = "store_true")
argparser.add_argument("-no-warnings", action = "store_false", dest = "warnings")

def main (argv):
    args = argparser.parse_args(argv)

    defaults = cl.OrderedDict(config.defaults)
    order = { param : i for i, param in enumerate(defaults.keys()) }

    for key, vals in iter_params(defaults, config.tests):
        if key in defaults:
            continue

        val = vals[0]
        pos = len(order)
        defaults[key] = val
        order[key] = pos

        if args.warnings:
            print("Using `{}` as default and `{}` as order for `{}`.".format(
                val, pos, key
            ))

    for key, val in iter_values(defaults, config.tests):
        config.preprocess(key, val)

    dat_fname = os.path.join(config.work_path, config.dat_fname)
    don_fname = os.path.join(config.work_path, config.don_fname)

    alist.mkfile(dat_fname, don_fname)
    o_type = "wb+" if args.clear else "rb+"

    with open(dat_fname, o_type) as queue, open(don_fname, o_type) as done:
        with flock.flock(queue), flock.flock(done):
            exists = set()

            for task in alist.iterate_locked(queue):
                exists.add(tuple(sorted(task)))

            created = alist.write_locked(queue, *(
                ts for ts in iter_tests(defaults, config.tests, order)
                    if tuple(sorted(ts)) not in exists
            ))

            for _ in range(created):
                done.seek(0, os.SEEK_END)
                done.write(config.sep_free)

            print("created", created, "experiments")

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
