#!/bin/bash

concurrentNumber=$1
api_url=$2
access_token=$3

python3 init_cgroup.py

mkdir log

date_time=$(date +"%Y_%m_%d_%H_%M_%S")

for i in $(seq 1 ${concurrentNumber})
do
    echo $i
    nohup python3 judge.py ${api_url} ${access_token} >>log/judge_${date_time}.log 2>&1 &
done
