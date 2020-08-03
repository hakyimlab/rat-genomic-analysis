#!/usr/bin/env python

#Author - Tyson Miller

import pandas as pd
import os

def parse_genotype(file, samples, filename):
  '''
  This takes a genotype file and a list of samples to keep and parses
  the genotype file to retain only those columns/samples. Make the dir
  variable the path to the directory you want to write the file to.
  '''

  df = pd.read_csv(file, sep='\t', engine = 'python')
  print(df.columns)

  df_filtered = df[samples]

  dir = './data/genotype'
  suffix = '.txt'
  path = os.join.path(dir, filename + suffix)
  df_filtered.to_csv(path, sep = '\t')


