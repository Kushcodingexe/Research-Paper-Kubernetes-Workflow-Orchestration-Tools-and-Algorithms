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
   "lfn": "kubeconfig",
   "id": 1,
   "src_urls": [
     { "site_label": "local", "url": "file:///tmp/pegasus-scratch/snu/pegasus/rack-resiliency-1x-20260122-134419/run0001/00/00/kubeconfig", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file://$PWD/kubeconfig" }
   ] }
]
eof

printf "\n##################### Checking file integrity for input files #####################\n"  1>&2
# do file integrity checks
pegasus-integrity --print-timings --verify=stdin 1>&2 << 'eof'
kubeconfig
eof

pegasus_lite_section_end stage_in
set +e
job_ec=0
pegasus_lite_section_start task_execute
printf "\n######################[Pegasus Lite] Executing the user task ######################\n"  1>&2
pegasus-kickstart  -n rack_resiliency::health-check:1.0 -N ID0000002 -R local  -s health-check-2.log=health-check-2.log -L rack-resiliency-1x-20260122-134419 -T 2026-01-22T13:44:19+05:30 /home/snu/kubernetes/Automation_Scripts/rack_resiliency_to_host.py health-check --stabilization-time=10
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
   "lfn": "health-check-2.log",
   "id": 1,
   "src_urls": [
     { "site_label": "local", "url": "file://$PWD/health-check-2.log", "checkpoint": "false" }
   ],
   "dest_urls": [
     { "site_label": "local", "url": "file:///tmp/pegasus-scratch/snu/pegasus/rack-resiliency-1x-20260122-134419/run0001/00/00/health-check-2.log" }
   ] }
]
eof

pegasus_lite_section_end stage_out

set -e


# clear the trap, and exit cleanly
trap - EXIT
pegasus_lite_final_exit

