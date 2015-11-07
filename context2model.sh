#!/usr/bin/env bash

more $1 | tee | python context2model.py $1 $2 $3
