# takes a file name from the command line and converts it, generating a csv
# in the same location as the argument
#
# Example: 
# python3 sample_client.py filename.spc
#
# would generate a csv named filename-DataSet[num].csv for every dataset in the spc file

import getSpectrum
import sys

getSpectrum.main(sys.argv[1])

