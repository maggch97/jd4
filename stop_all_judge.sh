#!/bin/bash

ps aux | grep judge.py | awk '{ print $2 }' | xargs kill -9
