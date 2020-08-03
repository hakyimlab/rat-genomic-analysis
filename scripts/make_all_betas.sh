#!/bin/bash
# Script to concatenate beta files split by chromosome together.

tissue=$1
allBetas=$2
alpha=$3
snpset=$4
i=0
for betafile in $(ls outputTW_${tissue}_elasticNet_alpha${alpha}_${snpset}_weights_chr*); do
	if [ $i -eq 0 ] ; then
		head -n 1 $betafile > $allBetas
		i=1
	fi
	tail -n +2 $betafile >> $allBetas
done

