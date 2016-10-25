#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  aaf_phylokmer.py
#  
#  Copyright 2015,2016 Huan Fan
#  <hfan22@wisc.edu> & Yann Surget-Groba <yann@xtbg.org.cn>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  

import sys, gzip, bz2, os, time
import multiprocessing as mp
from optparse import OptionParser

def smartopen(filename,*args,**kwargs):
    if filename.endswith('gz'):
        return gzip.open(filename,*args,**kwargs)
    elif filename.endswith('bz2'):
        return bz2.BZ2File(filename,*args,**kwargs)
    else:
        return open(filename,*args,**kwargs)

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)



usage = "usage: %prog [options]"
version = '%prog 20161025.1'
parser = OptionParser(usage = usage, version = version)
parser.add_option("-k", dest = "kLen", type = int, default = 25,
				  help = "k for reconstruction, default = 25")
parser.add_option("--ks", dest = "ksLen", type = int, default = 25,
				  help = "k for reads selection, default = 25")
parser.add_option("-n", dest = "filter", type = int, default = 1,
				  help = "k-mer filtering threshold, default = 1")
parser.add_option("-d", dest = "dataDir", default = 'data',
				  help = "directory containing the data, default = data/")
parser.add_option("-G", dest = "memSize", type = int, default = 4,
				  help = "total memory limit (in GB), default = 4")
parser.add_option("-t", dest = "nThreads", type = int, default = 1,
				  help = "number of threads to use, default = 1")
parser.add_option("-l", dest = "long", action = 'store_true',
				  help = "use fitch_kmerX_long instead of fitch_kmerX")

(options, args) = parser.parse_args()

nThreads = options.nThreads
n = options.filter
memPerThread = int(options.memSize / float(nThreads))
kl = options.kLen
ks = options.ksLen
dataDir = options.dataDir

if not memPerThread:
    print 'Not enough memory, decrease nThreads or increase memSize'
    sys.exit()
    

###check the data directory:
if not os.path.isdir(dataDir):
    print 'Cannot find data directory {}'.format(dataDir)
    sys.exit(2)


###check for the executable files:
#kmer_merge
if os.system('which kmer_merge > /dev/null'):
    filt = './kmer_merge'
    if not is_exe(filt):
        print 'kmer_merge not found. Make sure it is in your PATH or the'
        print 'current directory, and that it is executable'
        sys.exit(1)
else:
    filt = 'kmer_merge'

#ReadsSelector
if os.system('which ReadsSelector > /dev/null'):
	ReadsSelector = './ReadsSelector'
	if not is_exe(filt):
        print('ReadsSelector not found. Make sure it is in your PATH or the')
	    print('current directory, and that it is executable')
	    sys.exit(1)
else:
	ReadsSelector = 'ReadsSelector'

#fitch
if os.system('which fitch_kmerX > /dev/null'):
	if options.long:
	    fitch = './fitch_kmerX_long'
	else:
        fitch = './fitch_kmerX'
	if not is_exe(fitch):
	    print(fitch+' not found. Make sure it is in your PATH or the')
	    print('current directory, and that it is executable')
	    sys.exit()
else:
	if options.long:
	    fitch = 'fitch_kmerX_long'
	else:
        fitch = 'fitch_kmerX'

###Get sample list:
samples = []
for fileName in os.listdir(dataDir):
    if os.path.isdir(os.path.join(dataDir, fileName)):
        samples.append(fileName)
    else:
        if not fileName.startswith('.'):
            sample = fileName.split(".")[0]
            if sample in samples:
                sample = fileName.split(".")[0]+fileName.split(".")[1]
                if sample in samples:
                    print 'Error, redundant sample or file names. Aborting!'
                    sys.exit(3)
            os.system("mkdir {}/{}".format(dataDir,sample))
            os.system("mv {}/{} {}/{}/".format(dataDir,fileName,dataDir,sample))
            samples.append(sample)
samples.sort()
sn = len(samples)

print time.strftime('%c')
print 'SPECIES LIST:'
for sample in samples:
    print sample


###Run aaf_kmercount to get pkdat for each species

aaf_kmercount(dataDir,samples,ks,n,options.nThreads,memSize/options.nThreads)

###Run kmer_merge
command_sba = "{} -k s -c -d '0' -a A".format(filt)

for i, sample in enumerate(samples):
    command_sba += " '{}.pkdat.gz'".format(sample)

command_sba += ' | cut -f 1 > sba.kmer'
sba_sh = open("kmer_merge.sh",'w')
sba_sh.write(command_sba)
sba_sh.close()

###Run kmer_merge.sh
command = 'sh kmer_merge.sh'
os.system(command)
print time.strftime('%c')

####set up directory for selected reads
selection_dir = '{}_ks{}_sba'.format(os.path.basename(dataDir.rstrip('/')),ks)

if os.path.exists('./'+selection_dir):
	command = 'rm -r {}'.format(selection_dir)
	os.system(command)
command = 'mkdir {}'.format(selection_dir)
os.system(command)

#Run ReadsSelector
for sample in samples:
	infiles = os.listdir(os.path.join(dataDir,sample):
	command = '{} -k sba.kmer -fa 1 -o {}/{}_selected ' \
				 .format(ReadsSelector,selection_dir,sample)
	for input in infiles:
		command += '-s {}'.format(infiles)
	os.system(command)
	
#After selection
aaf_kmercount(selection_dir,samples,ks,n,options.nThreads,memSize/options.nThreads)