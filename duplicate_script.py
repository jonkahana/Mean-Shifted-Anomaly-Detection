import numpy as np
import os
from os.path import join
import shutil
from copy import deepcopy

# project_path = '/cs/labs/peleg/nivc/disentangled_ad/DCoDR/'
project_path = '/Users/jonatankahana/Desktop/jonathan/projects/Red_PANDA/Mean-Shifted-Anomaly-Detection'

files_to_duplicate = [
    'bash_scripts/cars3d__az_id.sh'
    # 'bash_scripts/regen_data'
]
is_folders = False

# all_alias_keys = ['DCoDR_norec']
# all_aliases = [['PANDA']]


all_alias_keys = ['cars3d__az_id']
all_aliases = [["celeba__short", "celeba__glass_prot__short", "celeba", "celeba__glass_prot"]]
# all_aliases = [["edges2shoes_x64__domain_vs_shoe_type", "edges2shoes_x64__domain_vs_shoe_type_short"]]
# all_aliases = [["rafd_full_0__angles_id", "rafd_full_1__angles_id", "rafd_full_2__angles_id", "rafd_full_3__angles_id", "rafd_full_4__angles_id",
#                 "cars3d__az_id", "cars3d__id_az", "cars3d_small_gaps__id_az", "mnist__digits_angle_short", "mnist_anom_hflip2__angle_digits_short",
#                 "mnist_anom_hflip__angle_digits_short", "mnist_hflip__angle_digits_short", "mnist_tilt60__digits_angle_short", "mnist_tilt120__digits_angle_short",
#                 "rafd__angles_id", "utk"]]

# all_alias_keys = ['recon_0_3', 'reconstruction-decay=0.3']
# all_alias_keys = ['cars3d']
# all_aliases = [['utk']]
# all_aliases = [
#     ['recon_0_1', 'recon_0_3', 'recon_0_5', 'recon_0_7', 'recon_1_0', 'recon_2_0', 'recon_5_0', 'recon_10_0'],
#     ['reconstruction-decay=0.1', 'reconstruction-decay=0.3', 'reconstruction-decay=0.5', 'reconstruction-decay=0.7',
#      'reconstruction-decay=1.0', 'reconstruction-decay=2.0', 'reconstruction-decay=5.0', 'reconstruction-decay=10.0']]
# all_aliases = ["rafd", "surprised_anom_rafd", "gen2_rafd", "gen2_surprised_anom_rafd"]
# all_alias_keys = ["tau=0.2", "tau_0_2", "shifting-args=\"[0.2]\""]
# all_aliases = [["tau=0.1", "tau=0.3"], ["tau_0_1", "tau_0_3"], ["shifting-args=\"[0.1]\"", "shifting-args=\"[0.3]\""]]


if type(all_alias_keys) != list:
    all_alias_keys = [all_alias_keys]
if type(all_aliases[0]) != list:
    all_aliases = [all_aliases]

assert len(np.unique([len(x) for x in all_aliases])) == 1
assert len(all_alias_keys) == len(all_aliases)

all_alias_keys, all_aliases = np.array(all_alias_keys), np.array(all_aliases)

if __name__ == '__main__':
    if is_folders:
        all_files = []
        for dirpath in files_to_duplicate:
            for root, _, files in os.walk(join(project_path, dirpath)):
                for filename in files:
                    filepath = join(root, filename)
                    all_files.append(filepath)
        files_to_duplicate = all_files
    for file_loc in files_to_duplicate:
        filepath = join(project_path, file_loc)
        for i in range(len(all_aliases[0])):
            cur_filepath = filepath
            with open(filepath, 'r') as orig_f:
                cur_lines = []
                for line in orig_f:
                    cur_lines.append(line)
            for alias_key, alias_val in zip(all_alias_keys, all_aliases[:, i]):
                cur_filepath = cur_filepath.replace(alias_key, alias_val)
                for j, line in enumerate(cur_lines):
                    new_line = line.replace(alias_key, alias_val)
                    cur_lines[j] = new_line
            if os.path.exists(cur_filepath):
                os.remove(cur_filepath)
            dirpath = '/'.join(cur_filepath.split('/')[:-1])
            os.makedirs(dirpath, exist_ok=True)
            with open(cur_filepath, 'a+') as new_f:
                for new_line in cur_lines:
                    new_f.write(new_line)
            print(cur_filepath)
