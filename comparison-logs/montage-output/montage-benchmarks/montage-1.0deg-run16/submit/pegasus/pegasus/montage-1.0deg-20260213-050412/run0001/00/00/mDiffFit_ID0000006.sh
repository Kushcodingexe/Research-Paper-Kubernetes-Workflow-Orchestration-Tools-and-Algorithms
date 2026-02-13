#!/bin/bash
set -e
pegasus_lite_version_major="5"
pegasus_lite_version_minor="0"
pegasus_lite_version_patch="9"
pegasus_lite_enforce_strict_wp_check="true"
pegasus_lite_version_allow_wp_auto_download="true"


. pegasus-lite-common.sh

pegasus_lite_init

# cleanup in case of failures
trap pegasus_lite_signal_int INT
trap pegasus_lite_signal_term TERM
trap pegasus_lite_unexpected_exit EXIT

printf "\n########################[Pegasus Lite] Setting up workdir ########################\n"  1>&2
# work dir
pegasus_lite_setup_work_dir

printf "\n##############[Pegasus Lite] Figuring out the worker package to use ##############\n"  1>&2
# figure out the worker package to use
pegasus_lite_worker_package

pegasus_lite_section_start stage_in
printf "\n###################### Staging in input data and executables ######################\n"  1>&2
# stage in data and executables
pegasus-transfer --threads 1  1>&2 << 'eof'
[
 { "type": "transfer",
   "linkage": "input",
   "lfn": "projected_001.fits",
   "id": 1,
   "src_urls": [
     { "site_label": "local", "url": "file:///app/scratch/pegasus/pegasus/montage-1.0deg-20260213-050412/run0001/00/00/projected_001.fits", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file://$PWD/projected_001.fits" }
   ] }
 ,
 { "type": "transfer",
   "linkage": "input",
   "lfn": "projected_002.fits",
   "id": 2,
   "src_urls": [
     { "site_label": "local", "url": "file:///app/scratch/pegasus/pegasus/montage-1.0deg-20260213-050412/run0001/00/00/projected_002.fits", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file://$PWD/projected_002.fits" }
   ] }
]
eof

printf "\n##################### Checking file integrity for input files #####################\n"  1>&2
# do file integrity checks
pegasus-integrity --print-timings --verify=stdin 1>&2 << 'eof'
projected_001.fits:projected_002.fits
eof

pegasus_lite_section_end stage_in
set +e
job_ec=0
pegasus_lite_section_start task_execute
printf "\n######################[Pegasus Lite] Executing the user task ######################\n"  1>&2
pegasus-kickstart  -n montage::mDiffFit:6.0 -N ID0000006 -R local  -s diff_001.fits=diff_001.fits -s fit_001.txt=fit_001.txt -L montage-1.0deg-20260213-050412 -T 2026-02-13T05:04:12+00:00 /app/executables/mDiffFit.py projected_001.fits projected_002.fits diff_001.fits fit_001.txt
job_ec=$?
pegasus_lite_section_end task_execute
set -e
pegasus_lite_section_start stage_out
printf "\n############################ Staging out output files ############################\n"  1>&2
# stage out
pegasus-transfer --threads 1  1>&2 << 'eof'
[
 { "type": "transfer",
   "linkage": "output",
   "lfn": "diff_001.fits",
   "id": 1,
   "src_urls": [
     { "site_label": "local", "url": "file://$PWD/diff_001.fits", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file:///app/scratch/pegasus/pegasus/montage-1.0deg-20260213-050412/run0001/00/00/diff_001.fits" }
   ] }
 ,
 { "type": "transfer",
   "linkage": "output",
   "lfn": "fit_001.txt",
   "id": 2,
   "src_urls": [
     { "site_label": "local", "url": "file://$PWD/fit_001.txt", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file:///app/scratch/pegasus/pegasus/montage-1.0deg-20260213-050412/run0001/00/00/fit_001.txt" }
   ] }
]
eof

pegasus_lite_section_end stage_out

set -e


# clear the trap, and exit cleanly
trap - EXIT
pegasus_lite_final_exit

