#!/bin/sh
# E4 (FR/IT) with the E3 design (names+desc, label memory k=5, identity order); starts when a lane frees its 4 workers
cd "$(dirname "$0")"
( until grep -q LANE1_DONE raw/lane1.log; do sleep 10; done; S3_DESC_E4=1 S3_E4_MEM=1 python3 -I run.py e4fra 4; echo E4FR_DONE ) > raw/lane_e4fr.log 2>&1 &
( until grep -q LANE2_DONE raw/lane2.log; do sleep 10; done; S3_DESC_E4=1 S3_E4_MEM=1 python3 -I run.py e4ita 4; echo E4IT_DONE ) > raw/lane_e4it.log 2>&1 &
wait
