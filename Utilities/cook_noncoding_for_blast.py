#!/usr/bin/env python
import sys
import os
path_of_this_script = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(os.path.join(path_of_this_script, ".."))
from Library.seq_parser import *

    
in_fasta = input('fasta:').strip()
f_matrix = read_fasta(in_fasta)
for i in range(len(f_matrix[0])):
    f_matrix[0][i] = 'noncoding '+f_matrix[0][i]
i = 0
del_count = 0
seq_sets = set()
while i < len(f_matrix[0]):
    if len(f_matrix[1][i]) < 50 or f_matrix[1][i] in seq_sets:
        del f_matrix[0][i]
        del f_matrix[1][i]
        del_count += 1
    else:
        seq_sets.add(f_matrix[1][i])
        i += 1
sys.stdout.write('delete '+str(del_count)+'\n')
out_fasta = open(in_fasta+'.new.fasta', 'w')
for i in range(len(f_matrix[0])):
    out_fasta.write('>'+f_matrix[0][i]+'\n'+f_matrix[1][i]+'\n')
out_fasta.close()