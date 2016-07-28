#!/usr/bin/env python
__author__ = 'Kinggerm'


import time
import string
import math
import os
import sys
from optparse import OptionParser, OptionGroup

# Local version 3.4

stop_codons = {"TAA", "TAG", "TGA", 'taa', 'tag', 'tga'}
initiation_codons = {"ATG", 'atg', "GTG", 'gtg', "ATT", 'att', "ATA", 'ata', "TTG", 'ttg', "ATC", 'atc', "CTG", 'ctg'}
try:
    # python2
    translator = string.maketrans("ATGCRMYKHBDVatgcrmykhbdv", "TACGYKRMDVHBtacgykrmdvhb")

    def complementary_seq(input_seq):
        return string.translate(input_seq, translator)[::-1]
except AttributeError:
    # python3
    translator = str.maketrans("ATGCRMYKHBDVatgcrmykhbdv", "TACGYKRMDVHBtacgykrmdvhb")

    def complementary_seq(input_seq):
        return str.translate(input_seq, translator)[::-1]


def get_parentheses_pairs(tree_string, sign=('(', ')')):
    tree_line = list(tree_string)
    left_sign = []
    count_ls = 0
    left_level = []
    right_sign = []
    count_rs = 0
    right_level = []
    if tree_line.count(sign[0]) == tree_line.count(sign[1]):
        for i in range(0, len(tree_line)):
            if tree_line[i] == sign[0]:
                left_sign.append(i)
                left_level.append(count_ls-count_rs)
                count_ls += 1
                right_sign.append(int)
                continue
            if tree_line[i] == sign[1]:
                count_rs += 1
                right_level.append(count_ls-count_rs)
                for j in range(0, count_ls):
                    if left_level[count_ls-1-j] == right_level[count_rs-1]:
                        right_sign[count_ls-1-j] = i
                        break
    else:
        raise Exception('Unbalanced signs in tree description: '+''.join(map(str, tree_line)))
    return left_sign, right_sign
# get_parentheses_pairs('th((i))s')
# get_parentheses_pairs('this')
# if long string, make this dict
utilize_types = {'gene', 'tRNA', 'rRNA', 'exon', 'intron', 'CDS'}


def read_annotation_of_gb(annotation_lines, seq_len, gb_name, by_site=True):
    # annotation_list[0] will not be utilized
    # annotation_list[1] means the dictionary for the 1st base
    # example for annotationlist[x]: [{'transl_table': '11', 'protein_id': '"BAK69443.1"', 'db_xref': '"GI:345433621"', 'product': '"hypothetical chloroplast RF2"', 'codon_start': '1', 'type': 'CDS', 'direction': 'reverse', 'gene': '"ycf2"'}, {'type': 'gene', 'direction': 'reverse', 'gene': '"ycf2"'}]
    if by_site:
        annotation_list = [[] for x in range(0, seq_len+1)]
    # parse lines
    regions_separate = []  # with noncoding
    regions_units = []  # without noncoding, continuous CDS
    error_in_gb = []
    for i in range(0, len(annotation_lines)):
        if annotation_lines[i][0] in utilize_types and 'gene=' not in ''.join(annotation_lines[i][2:]):
            error_in_gb.append('\t'.join(annotation_lines[i]))
        elif annotation_lines[i][0] in utilize_types and 'gene=' in ''.join(annotation_lines[i][2:]):
            # delete join() and order()
            while 'join' in annotation_lines[i][1]:
                join_loc = annotation_lines[i][1].index('join')
                pairs = get_parentheses_pairs(annotation_lines[i][1])
                right = pairs[1][pairs[0].index(join_loc+4)]
                annotation_lines[i][1] = annotation_lines[i][1][:right]+annotation_lines[i][1][right+1:]
                annotation_lines[i][1] = annotation_lines[i][1][:join_loc]+annotation_lines[i][1][join_loc+5:]
            while 'order' in annotation_lines[i][1]:
                order_loc = annotation_lines[i][1].index('order')
                pairs = get_parentheses_pairs(annotation_lines[i][1])
                right = pairs[1][pairs[0].index(order_loc+5)]
                annotation_lines[i][1] = annotation_lines[i][1][:right]+annotation_lines[i][1][right+1:]
                annotation_lines[i][1] = annotation_lines[i][1][:order_loc]+annotation_lines[i][1][order_loc+6:]
            # assume all parentheses left are complements
            # find out all complements
            annotation_lines[i][1] = annotation_lines[i][1].replace('complement', '')
            complements = get_parentheses_pairs(annotation_lines[i][1])
            # find out all region pairs
            ellipsis = {}
            for l in range(0, len(annotation_lines[i][1])-1):
                if annotation_lines[i][1][l:l+2] == '..':
                    ellipsis[l] = 'forward'
                    # and find out the directions according to the position of complement tag -- left parentheses
                    for m in range(0, len(complements[0])):
                        if complements[0][m] < l < complements[1][m]:
                            ellipsis[l] = 'reverse'
                            break
            ellipsis_key = [x for x in ellipsis]
            ellipsis_key.sort()
            # read into regions_separate
            unit_dict = {'type': annotation_lines[i][0]}
            for j in range(2, len(annotation_lines[i])):
                unit_dict[annotation_lines[i][j].split('=')[0]] = '='.join(annotation_lines[i][j].split('=')[1:]).strip('"').strip('\'')
            regions_units.append([[], [], unit_dict])
            #
            region_parts = [[int(y.replace('>', '').replace('<', '')) for y in x.split('..')] for x in annotation_lines[i][1].replace('(', '').replace(')', '').split(',')]
            for l in range(0, len(region_parts)):
                this_direction = ellipsis[ellipsis_key[l]]
                this_start = region_parts[l][0]
                this_end = region_parts[l][1]
                #
                separate_dict = {'type': annotation_lines[i][0], 'direction': this_direction}
                for j in range(2, len(annotation_lines[i])):
                    separate_dict[annotation_lines[i][j].split('=')[0]] = '='.join(annotation_lines[i][j].split('=')[1:]).strip('"').strip('\'')
                #
                regions_separate.append([this_start, this_end, separate_dict])
                #
                regions_units[-1][0].append((this_start, this_end))
                regions_units[-1][1].append(this_direction)
                if by_site:
                    for base in range(region_parts[l][0], region_parts[l][1]+1):
                        annotation_list[base].append(separate_dict)
    if error_in_gb:
        sys.stdout.write('\nUnrecognized annotations in '+gb_name+':')
        for error_line in error_in_gb:
            sys.stdout.write('\n'+error_line)
        sys.stdout.write('\n')
    # locate region that occupied by genes
    names = {}
    gene_regions = []
    gene_regions += [x for x in regions_separate if x[2]['type'] == 'CDS']
    for x in gene_regions:
        names[x[2]['gene']] = 0
    gene_regions += [x for x in regions_separate if x[2]['type'] == 'tRNA' and x[2]['gene'] not in names]
    for x in gene_regions:
        names[x[2]['gene']] = 0
    gene_regions += [x for x in regions_separate if x[2]['type'] == 'rRNA' and x[2]['gene'] not in names]
    for x in gene_regions:
        names[x[2]['gene']] = 0
    gene_regions += [x for x in regions_separate if x[2]['type'] == 'intron' and x[2]['gene'] not in names]
    gene_regions.sort(key=lambda x:x[0])
    gene_regions_last = gene_regions[:]
    gene_regions_last.sort(key=lambda x:x[1])
    # fill the start with IGS
    if gene_regions[0][0] > 1:
        separate_dict = {'type': 'IGS', 'direction': 'none', 'gene': gene_regions_last[-1][2]['gene']+'--'+gene_regions[0][2]['gene']}
        regions_separate.append([1, gene_regions[0][0]-1, separate_dict])
        if by_site:
            for base in range(1, gene_regions[0][0]):
                annotation_list[base].append(separate_dict)
    # fill the end with IGS
    if gene_regions_last[-1][1] < seq_len:
        separate_dict = {'type': 'IGS', 'direction': 'none', 'gene': gene_regions_last[-1][2]['gene']+'--'+gene_regions[0][2]['gene']}
        regions_separate.append([gene_regions_last[-1][1]+1, seq_len, separate_dict])
        if by_site:
            for base in range(gene_regions_last[-1][1]+1, seq_len+1):
                annotation_list[base].append(separate_dict)
    del gene_regions_last
    # fill the middle with IGS
    for i in range(0, len(gene_regions)-1):
        if gene_regions[i][1] < gene_regions[i+1][0]-1:
            separate_dict = {'type': 'IGS', 'direction': 'none', 'gene': gene_regions[i][2]['gene']+'--'+gene_regions[i+1][2]['gene']}
            regions_separate.append([gene_regions[i][1]+1, gene_regions[i+1][0]-1, separate_dict])
            if by_site:
                for base in range(gene_regions[i][1]+1, gene_regions[i+1][0]):
                    annotation_list[base].append(separate_dict)
    regions_separate.sort(key=lambda x:(x[0], x[1]))
    if by_site:
        return {'by_region': regions_separate, 'by_unit': regions_units, 'by_site': annotation_list}
    else:
        return {'by_region': regions_separate, 'by_unit': regions_units}


def read_gb(gb_dir):
    gb_file = [x.strip('\n') for x in open(gb_dir, 'rU').readlines()]
    i = 0
    gb_structure = {}
    while i < len(gb_file):
        gb_structure[gb_file[i].split('  ')[0]] = {'description':'  '.join([x.strip() for x in gb_file[i].split('  ')[1:] if x])}
        j = i + 1
        # special
        if gb_file[i].split('  ')[0] in ['FEATURES']:
            gb_structure[gb_file[i].split('  ')[0]]['Annotations lines'] = []
        elif gb_file[i].split('  ')[0] in ['LOCUS']:
            locus_line = [x for x in gb_file[i].split(' ') if x]
            gb_structure[gb_file[i].split('  ')[0]]['name'] = locus_line[1]
            gb_structure[gb_file[i].split('  ')[0]]['sequence length'] = int(locus_line[locus_line.index('bp')-1])
        elif gb_file[i].split('  ')[0] in ['ORIGIN']:
            gb_structure[gb_file[i].split('  ')[0]]['sequence'] = ''
        # batch reading
        while j < len(gb_file) and gb_file[j].startswith(' '):
            #
            blank_len = 0
            while blank_len < len(gb_file[j]):
                if gb_file[j][blank_len] != ' ':
                    break
                blank_len += 1
            if gb_file[i].split('  ')[0] not in ['FEATURES', 'ORIGIN', 'BASE COUNT']:
                temp = [x for x in gb_file[j].split(' ') if x]
                this_title = temp[0]
                this_content = [' '.join(temp[1:])]
                while j + 1 < len(gb_file) and gb_file[j+1].startswith(' '*(blank_len+4)):
                    this_content.append(gb_file[j+1].strip())
                    j += 1
                gb_structure[gb_file[i].split(' ')[0]][this_title] = this_content
            elif gb_file[i].split('  ')[0] in ['FEATURES']:
                temp = [x for x in gb_file[j].split(' ') if x]
                while j + 1 < len(gb_file) and gb_file[j+1].startswith(' '*(blank_len+4)):
                    if gb_file[j+1].strip().startswith('/'):
                        temp.append(gb_file[j+1].strip()[1:])
                    else:
                        temp[-1] += gb_file[j+1].strip()
                    j += 1
                gb_structure[gb_file[i].split('  ')[0]]['Annotations lines'].append(temp)
            elif gb_file[i].split('  ')[0] in ['ORIGIN']:
                this_sequence = ''
                read_line = gb_file[j].strip().split()
                while j < len(gb_file) and read_line[0].isdigit():
                    this_sequence += ''.join(read_line[1:])
                    j += 1
                    read_line = gb_file[j].strip().split()
                gb_structure[gb_file[i].split('  ')[0]]['sequence'] = this_sequence
            else:
                #
                pass
            j += 1
        i = j
    return gb_structure['LOCUS']['name'], gb_structure['ORIGIN']['sequence'], gb_structure['FEATURES']['Annotations lines']


def write_fasta(out_dir, matrix, overwrite):
    if not overwrite:
        while os.path.exists(out_dir):
            out_dir = '.'.join(out_dir.split('.')[:-1])+'_.'+out_dir.split('.')[-1]
    fasta_file = open(out_dir, 'w')
    if matrix[2]:
        for i in range(len(matrix[0])):
            fasta_file.write('>'+matrix[0][i]+'\n')
            j = matrix[2]
            while j < len(matrix[1][i]):
                fasta_file.write(matrix[1][i][(j-matrix[2]):j]+'\n')
                j += matrix[2]
            fasta_file.write(matrix[1][i][(j-matrix[2]):j]+'\n')
    else:
        for i in range(len(matrix[0])):
            fasta_file.write('>'+matrix[0][i]+'\n')
            fasta_file.write(matrix[1][i]+'\n')
    fasta_file.close()


def read_fasta(fasta_dir):
    fasta_file = open(fasta_dir, 'rU')
    names = []
    seqs = []
    this_line = fasta_file.readline()
    while this_line:
        if this_line.startswith('>'):
            names.append(this_line[1:].strip())
            this_seq = ''
            this_line = fasta_file.readline()
            while this_line and not this_line.startswith('>'):
                this_seq += this_line.strip()
                this_line = fasta_file.readline()
            seqs.append(this_seq)
        else:
            this_line = fasta_file.readline()
    fasta_file.close()
    return [names, seqs]


def read_gb_as_geneious_format_fasta_matrix(gb_dir):
    sample_name, sequence, annotation_lines = read_gb(gb_dir)
    annotations = read_annotation_of_gb(annotation_lines, len(sequence), gb_dir, by_site=False)
    names = []
    seqs = []
    for region in annotations['by_unit']:
        #
        if (region[2]['gene'].startswith('trn') or region[2]['gene'].startswith('tRNA')) and len(region[1]) > 1:
            for i in range(len(region[0])):
                if region[1][i] == 'reverse':
                    seqs.append(complementary_seq(sequence[region[0][i][0]-1:region[0][i][1]]))
                else:
                    seqs.append(sequence[region[0][i][0]-1:region[0][i][1]])
                names.append((sample_name+' - '+region[2]['gene']+' exon '+str(i)).replace(' ', '_'))
        else:
            this_seq = ''
            for i in range(len(region[0])):
                if region[1][i] == 'reverse':
                    this_seq += complementary_seq(sequence[region[0][i][0]-1:region[0][i][1]])
                else:
                    this_seq += sequence[region[0][i][0]-1:region[0][i][1]]
            seqs.append(this_seq)
            #
            if 'gene' in region[2]:
                names.append((sample_name+' - '+region[2]['gene']+' '+region[2]['type']).replace(' ', '_'))
            # actually unnecessary
            else:
                names.append((sample_name+' - '+region[2]['name']+' '+region[2]['type']).replace(' ', '_'))
    # write_fasta(gb_dir+'.fasta', [names, seqs, 70], True)
    return [names, seqs]


def parse_geneious_fasta(fasta_matrix):
    seq_dict = {}
    for i in range(len(fasta_matrix[0])):
        this_annotation = fasta_matrix[0][i].split('_-_')[-1]
        if this_annotation in seq_dict:
            if fasta_matrix[1][i] not in seq_dict[this_annotation]:
                seq_dict[this_annotation].append(fasta_matrix[1][i])
        else:
            seq_dict[this_annotation] = [fasta_matrix[1][i]]
    return seq_dict, list(seq_dict)


transfer = {}
for char in string.ascii_lowercase:
    transfer[(char, char)] = 0
    transfer[(char, char.upper())] = 0
    transfer[(char.upper(), char)] = 0
    transfer[(char.upper(), char.upper())] = 0


def find_string_difference(this_string, this_reference, dynamic_span=2.0):
    len_str = len(this_string)
    len_ref = len(this_reference)
    if dynamic_span == 0:
        difference = sum([not (this_string[i], this_reference[i]) in transfer for i in range(min(len_ref, len_str))])+abs(len_ref-len_str)
        proper_end = this_string[-1] == this_reference[-1]
        return difference, proper_end
    else:
        dynamic_span = max(abs(len(this_string)-len(this_reference))+1, dynamic_span)
        this_match = int(not (this_string[0], this_reference[0]) in transfer)
        this_matrix = {(0, 0): {'state': this_match}}
        # calculate the first column
        for i in range(1, min(int(math.ceil(dynamic_span))+1, len_str)):
            this_matrix[(i, 0)] = {'right_out': this_match+i, 'state': this_match+i}
        # calculate the first line
        for j in range(1, min(int(math.ceil(dynamic_span))+1, len_ref)):
            this_matrix[(0, j)] = {'right_out': this_match+j, 'state': this_match+j}
        # calculate iteratively
        start = 0
        for i in range(1, len_str):
            start = max(1, int(i-dynamic_span))
            end = min(len_ref, int(math.ceil(i+dynamic_span)))
            # start: no right_in
            this_match = int(not (this_string[i], this_reference[start]) in transfer)
            this_matrix[(i, start)] = {'diagonal_out': this_matrix[(i-1, start-1)]['state'] + this_match,
                                       'down_out': this_matrix[(i-1, start)]['state'] + 1}
            this_matrix[(i, start)]['state'] = min(this_matrix[(i, start)].values())
            # middle
            for j in range(start+1, end-1):
                this_match = not (this_string[i], this_reference[j]) in transfer
                this_matrix[(i, j)] = {'diagonal_out': this_matrix[(i-1, j-1)]['state'] + this_match,
                                       'down_out': this_matrix[(i-1, j)]['state'] + 1,
                                       'right_out': this_matrix[(i, j-1)]['state'] + 1}
                this_matrix[(i, j)]['state'] = min(this_matrix[(i, j)].values())
            # end
            this_match = not (this_string[i], this_reference[end - 1]) in transfer
            this_matrix[(i, end-1)] = {'diagonal_out': this_matrix[(i-1, end-2)]['state'] + this_match}
            if (i, end-2) in this_matrix:
                this_matrix[(i, end-1)]['right_out'] = this_matrix[(i, end-2)]['state'] + 1
            this_matrix[(i, end-1)]['state'] = min(this_matrix[(i, end-1)].values())
        # print time.time()-time0
        difference = this_matrix[(len_str-1, len_ref-1)]['state']
        proper_end = True
        for j in range(start, len_ref):
            try:
                if this_matrix[(len_str-1, j)]['state'] < difference:
                    proper_end = False
                    break
            except KeyError:
                pass
        for i in range(max(0, len_str-len_ref+start), len_str):
            try:
                if this_matrix[(i, len_ref-1)]['state'] < difference:
                    proper_end = False
                    break
            except KeyError:
                pass
        return difference, proper_end


def require_commands():
    usage = "python this_script.py -q Query.gb -r Reference.gb" \
            "\n\nThis script only checks the mainly check the reliability of automatically annotated tRNA and CDS." \
            "\nBy jinjianjun@mail.kib.ac.cn"
    parser = OptionParser(usage=usage)
    group_need = OptionGroup(parser, "NECESSARY OPTIONS")
    group_need.add_option('-g', dest='query_gb', help='input query *.gb file')
    group_need.add_option('-r', dest='reference_gb', help='input reference *.gb file')  # , default='Reference.gb'
    group_alternation = OptionGroup(parser, "ALTERNATION of NECESSARY OPTIONS")
    group_alternation.add_option('-q', dest='query_fasta', help='input query fasta file exported by "Extract Annotations"-"Export"-"Selected Documents"-fasta in Geneious, remember to choose "Replace spaces in sequence name with underscores"')
    group_alternation.add_option('-d', dest='reference_fasta', help='input reference fasta file exported in the same way as above')
    group_optional = OptionGroup(parser, "OPTIONAL OPTIONS")
    group_optional.add_option('--t-ends', dest='ends_trna', help='Default=10. The length to check at the both ends of tRNA.', type=int, default=10)
    group_optional.add_option('--c-ends', dest='ends_cds', help='Default:not activated. Activate this calculation and assign the length to check at the both ends of CDS.', type=int)
    group_optional.add_option('--a-ends', dest='ends_all', help='Default:not activated. Activate this calculation and assign the length to check at the both ends of annotated all regions.', type=int)
    group_optional.add_option('--l-threshold', dest='length', help='Default=0.9. Length threshold to report warning.', type=float, default=0.9)
    group_optional.add_option('--similarity', dest='enable_similarity', help='Default=False. Choose to enable similarity calculation.', default=False, action='store_true')
    group_optional.add_option('--s-threshold', dest='similarity', help='Default=0.9. Similarity threshold to report warning. Should be < length threshold.', type=float, default=0.9)
    parser.add_option_group(group_need)
    parser.add_option_group(group_alternation)
    parser.add_option_group(group_optional)
    (options, args) = parser.parse_args()
    return options


def check_stop(sequences):
    to_return = True
    for seq in sequences:
        seq_len = len(seq)
        if seq_len % 3 != 0:
            to_return = False
            break
        else:
            if seq[seq_len-3:seq_len] not in stop_codons:
                to_return = False
                break
            else:
                for i in range(0, seq_len-3, 3):
                    if seq[i:i+3] in stop_codons:
                        to_return = False
                        break
    return to_return


def check_start(sequences):
    to_return = True
    for seq in sequences:
        if seq[:3] not in initiation_codons:
            to_return = False
    return to_return


def check_length(query_seqs, refer_seqs, length_threshold):
    to_return = True
    for q_seq in query_seqs:
        len_query = len(q_seq)
        len_differ_ratios = []
        for r_seq in refer_seqs:
            len_refer = len(r_seq)
            len_differ_ratios.append(abs(len_refer-len_query)/float(len_refer))
        if 1-min(len_differ_ratios) < length_threshold:
            to_return = False
            break
    return to_return


def check_similarity(query_seqs, refer_seqs, similarity_threshold, length_threshold):
    to_return = True
    for q_seq in query_seqs:
        base_differ_ratios = []
        for r_seq in refer_seqs:
            base_differ_ratios.append(find_string_difference(q_seq, r_seq, len(r_seq)*(1-length_threshold)/2)[0]/float(len(r_seq)))
        if 1-min(base_differ_ratios) < similarity_threshold:
            to_return = False
            break
    return to_return


def check_ends(query_seqs, refer_seqs, length_threshold, ends_length):
    to_return = True
    for q_seq in query_seqs:
        proper_starts = []
        for r_seq in refer_seqs:
            proper_starts.append(find_string_difference(q_seq[-ends_length:], r_seq[-ends_length:], len(r_seq)*(1-length_threshold)/2)[1])
        if not max(proper_starts):
            to_return = False
            break
        proper_ends = []
        for r_seq in refer_seqs:
            proper_ends.append(find_string_difference(q_seq[:ends_length][::-1], r_seq[:ends_length][::-1], len(r_seq)*(1-length_threshold)/2)[1])
        if not max(proper_ends):
            to_return = False
            break
    return to_return


def length_similarity(query_seqs, refer_seqs):
    to_returns = []
    for q_seq in query_seqs:
        len_query = len(q_seq)
        len_differ_ratios = []
        for r_seq in refer_seqs:
            len_refer = len(r_seq)
            len_differ_ratios.append(abs(len_refer-len_query)/float(len_refer))
        to_returns.append(1-min(len_differ_ratios))
    return min(to_returns)


def main():
    time0 = time.time()
    options = require_commands()
    time_tag = '='*35+'\nKinggerm @ '+time.asctime(time.localtime(time.time()))+'\n'+'='*35
    print(time_tag)
    pseudo_block = ['\nABNORMAL GENES:\n']
    not_in_query = ['\nNOT IN QUERY ERROR:\n']
    not_in_refer = ['\nNOT IN REFER ERROR:\n']
    alternations = ['\nALTERNATION CHOICE:\n']
    """read query"""
    try:
        q_matrix = read_gb_as_geneious_format_fasta_matrix(options.query_gb)
    except:
        try:
            q_matrix = read_fasta(options.query_fasta)
        except:
            sys.stdout.write("Error: No available query found!\n")
            os._exit(0)
    q_dict, q_names = parse_geneious_fasta(q_matrix)
    """read reference"""
    try:
        ref_matrix = read_gb_as_geneious_format_fasta_matrix(options.reference_gb)
    except:
        try:
            ref_matrix = read_fasta(options.reference_fasta)
        except:
            sys.stdout.write("Error: No available reference found!")
            os._exit(0)
    ref_dict, ref_names = parse_geneious_fasta(ref_matrix)
    """check query annotations"""
    for annotation in q_names:
        # print annotation
        if ';_' in annotation:
            for q_seq in q_dict[annotation]:
                scores = []
                for sub_annotation in annotation.split(';_'):
                    if sub_annotation not in ref_dict:
                        not_in_refer.append('  '+sub_annotation+' of _'+annotation+'\n')
                        scores.append([0, sub_annotation])
                    else:
                        ratios = []
                        for r_seq in ref_dict[sub_annotation]:
                            seq_len = float(len(r_seq))
                            ratios.append((seq_len-find_string_difference(q_seq, r_seq, 0)[0])/seq_len)
                        scores.append([max(ratios), sub_annotation])
                scores.sort(key=lambda x: -x[0])
                alternations.append('  >'+'; '.join([x[1]+':'+str(round(x[0], 2)) for x in scores])+'\n  '+q_seq+'\n')
        else:
            if annotation not in ref_dict:
                not_in_refer.append('  '+annotation+'\n')
            else:
                if not min([len(x.strip()) for x in q_dict[annotation]]):
                    pseudo_block.append('  Losing entire '+annotation+'\n')
                elif annotation.endswith('_CDS') or annotation.endswith('_cds'):
                    if not check_stop(q_dict[annotation]):
                        pseudo_block.append('  Stop codon of '+annotation+'\n')
                    elif not check_start(q_dict[annotation]):
                        pseudo_block.append('  Initiation of '+annotation+'\n')
                    elif not check_length(q_dict[annotation], ref_dict[annotation], options.length):
                        pseudo_block.append('  Length of '+annotation+'\n')
                    elif options.enable_similarity and not check_similarity(q_dict[annotation], ref_dict[annotation], options.similarity, options.length):
                        pseudo_block.append('  Similarity of '+annotation+'\n')
                    elif options.ends_cds and not check_ends(q_dict[annotation], ref_dict[annotation], options.length, options.ends_cds):
                        pseudo_block.append('  Start/&End of '+annotation+'\n')
                elif annotation.endswith('_trna') or annotation.endswith('_tRNA'):
                    if not check_length(q_dict[annotation], ref_dict[annotation], options.length):
                        pseudo_block.append('  Length of '+annotation+'\n')
                    elif not check_ends(q_dict[annotation], ref_dict[annotation], options.length, options.ends_trna):
                        pseudo_block.append('  Start/&End of '+annotation+'\n')
                    elif options.enable_similarity and not check_similarity(q_dict[annotation], ref_dict[annotation], options.similarity, options.length):
                        pseudo_block.append('  Similarity of '+annotation+'\n')
                else:
                    if options.ends_all and not check_ends(q_dict[annotation], ref_dict[annotation], options.length, options.ends_all):
                        pseudo_block.append('  Start/&End of '+annotation+'\n')
    for annotation in ref_names:
        if annotation not in q_dict:
            not_in_query.append('  '+annotation+'\n')
    if options.query_gb:
        out_log = open(options.query_gb+'.check.log', 'a')
    else:
        out_log = open(options.query_fasta+'.check.log', 'a')
    out_log.write(time_tag+'\n')
    for line in [pseudo_block[0]]+sorted(pseudo_block[1:])+[not_in_query[0]]+sorted(not_in_query[1:])\
            +[not_in_refer[0]]+not_in_refer[1:]+[alternations[0]]+alternations[1:]:
        sys.stdout.write(line)
        out_log.write(line)
    cost_time = '\n\nCost: '+str(round(time.time()-time0, 4))+'s\n'
    sys.stdout.write(cost_time)
    out_log.write(cost_time)
    out_log.close()


if __name__ == '__main__':
    main()
