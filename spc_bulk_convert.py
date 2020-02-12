#!/usr/bin/env python3

"""Shimadzu SPC file bulk converter.

Finds all spc file in the given directory and converts them to CSV.
See https://github.com/uri-t/shimadzu-spc-converter for more details

Usage:
  spc_bulk_convert.py <directory>
  spc_bulk_convert.py -h | --help

Options:
  -h --help     Show this screen.
"""
from docopt import docopt
from pathlib import Path
from getSpectrum import main


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Naval Fate 2.0')
    
    directory = arguments['<directory>']
    for spc_file in Path(directory).glob('**/*.spc'):
        spc_file = str(spc_file)

        with open(spc_file, 'rb') as f:
            signature = f.read(4)

        if signature == b'\xD0\xCF\x11\xE0':
            main(spc_file)
            print('converted ' + spc_file)
        else:
            print('Not OLE CF type file format, skipping: ' + spc_file)

