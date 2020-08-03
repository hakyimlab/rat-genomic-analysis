#!/usr/bin/env python

SOURCE_DIR = './output/
TARGET_DIR = '.output/'
RESULTS_DIR = 'allResults/'
BETAS_DIR = 'allBetas/'
LOGS_DIR = 'allLogs/'
SAMPLE_INFO_DIR = 'allMetaData/'

BETAS_INCLUDE_CLAUSE = ".allBetas."
RESULTS_INCLUDE_CLAUSE = ".allResults."
LOGS_INCLUDE_CLAUSE = '.allLogs.'
SAMPLE_INFO_INCLUDE_CLAUSE = '.allMetaData.'

BETA_HEADER_TOKENS = {"gene", "rsid", "ref", "alt", "beta", "alpha"}
RESULTS_HEADER_TOKENS = {"gene", "alpha", "cvm", "lambda.iteration", "lambda.min", "n.snps", "R2", "pval", "genename"}
LOGS_HEADER_TOKENS = {"chr", "n_genes", "seed_for_cv", "alpha"}
SAMPLE_INFO_HEADER_TOKENS = {"n_samples", "n_folds_cv", "snpset", "rsid_db_snp_label", "alpha"}

import gzip
import os
import sys
import sqlite3


def smart_open(source_file):
    if source_file.endswith('.txt'):
        return open(source_file)
    elif source_file.endswith('.gz'):
        return gzip.open(source_file)
    else:
        print "error: source file names should end in .txt or .gz; %s doesn't comply. exiting."%source_file
        sys.exit(1)


def smart_list(source_dir, including):
    source_files = [x for x in os.listdir(source_dir) if including in x]
    if len(source_files) == 0:
        print "warning: no recognized source files (i.e., including %s) on %s"%(including, source_dir)
    return sorted(source_files)


def source_files(source_dir, include_clause):
    "List all relevant source files."
    for x in in smart_list(source_dir, including=include_clause):
        yield os.path.join(source_dir, x)


def upconvert(x):
    for f in (int, float):
        try:
            return f(x)
        except ValueError:
            pass
    return x


class MetaDB:
    "This handles all the DBs for each source file (tissue type)"
    def __init__(self, source_file):
        self.source_file = source_file
        self.dbs = {} # alpha -> DB object

    def insert_row(self, row):
        alpha = row['alpha']
        if alpha not in self.dbs:
            self.dbs[alpha] = DB(self.source_file, alpha)
        self.dbs[alpha].insert_row(row)

    def close(self):
        for db in self.dbs.values():
            db.close()

def generate_weights_file():

    def data_rows_in(source_file):
        "Iterate over data rows in the source file, labeling fields and converting formats as required."
        header = None
        for k, line in enumerate(smart_open(source_file)):
            if k == 0:
                if not BETA_HEADER_TOKENS == set(line.strip().split()):
                    raise RuntimeError("Invalid header. We no longer assume anything.")
                header = line.strip().split()
            else:
                yield dict(zip(header, map(upconvert, line.strip().split())))

    class DB:
        "This encapsulates a single SQLite DB (for a given source file and alpha)."
        def __init__(self, source_file, alpha, target_dir=TARGET_DIR):
            tissue_name = os.path.basename(source_file).split('.')[0]
            db_filename = os.path.join(target_dir, '%s_%s.db'%(tissue_name, alpha))
            if not os.path.exists(target_dir):
                os.mkdir(target_dir)

            if os.path.exists(db_filename):
                os.unlink(db_filename)

            self.connection = sqlite3.connect(db_filename)

            self("CREATE TABLE weights (rsid TEXT, gene TEXT, weight DOUBLE, ref_allele CHARACTER, eff_allele CHARACTER, pval DOUBLE, N INTEGER, cis INTEGER)")
            self("CREATE INDEX weights_rsid ON weights (rsid)")
            self("CREATE INDEX weights_gene ON weights (gene)")
            self("CREATE INDEX weights_rsid_gene ON weights (rsid, gene)")


        def __call__(self, sql, args=None):
            c = self.connection.cursor()
            if args:
                c.execute(sql, args)
            else:
                c.execute(sql)

        def close(self):
            self.connection.commit()

        def insert_row(self, row):
            self("INSERT INTO weights VALUES(?, ?, ?, ?, ?, NULL, NULL, NULL)", (row['rsid'], row['gene'], row['beta'], row['ref'],row['alt']))
            "alt allele is the dosage/effect allele in GTEx data"

    for source_file in source_files(os.path.join(SOURCE_DIR, BETAS_DIR), BETAS_INCLUDE_CLAUSE):
        print "Processing %s..." %source_file
        meta_db = MetaDB(source_file=source_file)
        for row in data_rows_in(source_file):
            meta_db.insert_row(row)
        meta_db.close()


def add_extra_data():
    def data_rows_in(source_file):
        "Iterate over data rows in the source file, labeling fields and converting formats as required."
        header = None
        for k, line in enumerate(smart_open(source_file)):
            if k == 0:
                if not RESULTS_HEADER_TOKENS == set(line.strip().split()):
                    raise RuntimeError("Invalid header. We no longer assume anything.")
                header = line.strip().split()
            else:
                yield dict(zip(header, map(upconvert, line.strip().split())))


    class DB:
        "This encapsulates a single SQLite DB (for a given source file and alpha)."
        def __init__(self, source_file, alpha, target_dir=TARGET_DIR):
            tissue_name = os.path.basename(source_file).split('.')[0]
            db_filename = os.path.join(target_dir, '%s_%s.db'%(tissue_name, alpha))
            assert(os.path.exists(db_filename))
            self.connection = sqlite3.connect(db_filename)

            self("DROP INDEX IF EXISTS extra_gene")
            self("DROP TABLE IF EXISTS extra")
            self("CREATE TABLE extra (gene TEXT, genename TEXT, R2 DOUBLE, `n.snps` INTEGER, pval DOUBLE)")
            self("CREATE INDEX extra_gene ON extra (gene)")


        def __call__(self, sql, args=None):
            c = self.connection.cursor()
            if args:
                c.execute(sql, args)
            else:
                c.execute(sql)

        def close(self):
            self.connection.commit()

        def insert_row(self, row):
            self("INSERT INTO extra VALUES(?, ?, ?, ?, ?)", (row['gene'], row['genename'], row['R2'], row['n.snps'], row['pval']))


    for source_file in source_files(os.path.join(SOURCE_DIR, RESULTS_DIR), RESULTS_INCLUDE_CLAUSE):
        print "Processing %s..." % source_file
        meta_db = MetaDB(source_file=source_file)
        for row in data_rows_in(source_file):
            meta_db.insert_row(row)
        meta_db.close()

def add_log_data():
    def data_rows_in(source_file):
        "Iterate over data rows in the source file, labeling fields and converting formats as required."
        header = None
        for k, line in enumerate(smart_open(source_file)):
            if k == 0:
                if not LOGS_HEADER_TOKENS == set(line.strip().split()):
                    raise RuntimeError("Invalid header. We no longer assume anything.")
                header = line.strip().split()
            else:
                yield dict(zip(header, map(upconvert, line.strip().split())))

    class DB:
        "This encapsulates a single SQLite DB (for a given source file and alpha)."
        def __init__(self, source_file, alpha, target_dir=TARGET_DIR):
            tissue_name = os.path.basename(source_file).split('.')[0]
            db_filename = os.path.join(target_dir, '%s_%s.db'%(tissue_name, alpha))
            assert(os.path.exists(db_filename))
            self.connection = sqlite3.connect(db_filename)

            self("DROP INDEX IF EXISTS construction_chr")
            self("DROP TABLE IF EXISTS construction")
            self("CREATE TABLE construction (chr INTEGER, `n.genes` INTEGER, `cv.seed` INTEGER)")
            self("CREATE INDEX construction_chr ON construction (chr)")


        def __call__(self, sql, args=None):
            c = self.connection.cursor()
            if args:
                c.execute(sql, args)
            else:
                c.execute(sql)

        def close(self):
            self.connection.commit()

        def insert_row(self, row):
            self("INSERT INTO construction VALUES(?, ?, ?)", (row['chr'], row['n_genes'], row['seed_for_cv']))

    for source_file in source_files(os.path.join(SOURCE_DIR,LOGS_DIR), LOGS_INCLUDE_CLAUSE):
        print "Processing %s..."%source_file
        meta_db = MetaDB(source_file=source_file)
        for row in data_rows_in(source_file):
            meta_db.insert_row(row)
        meta_db.close()


def add_sample_data():
    def data_rows_in(source_file):
        "Iterate over data rows in the source file, labeling fields and converting formats as required."
        header = None
        for k, line in enumerate(smart_open(source_file)):
            if k == 0:
                if not SAMPLE_INFO_HEADER_TOKENS == set(line.strip().split()):
                    raise RuntimeError("Invalid header. We no longer assume anything.")
                header = line.strip().split()
            else:
                yield dict(zip(header, map(upconvert, line.strip().split())))

    class DB:
        "This encapsulates a single SQLite DB (for a given source file and alpha)."
        def __init__(self, source_file, alpha, target_dir=TARGET_DIR):
            tissue_name = os.path.basename(source_file).split('.')[0]
            db_filename = os.path.join(target_dir, '%s_%s.db'%(tissue_name, alpha))
            assert(os.path.exists(db_filename))
            self.connection = sqlite3.connect(db_filename)

            self("DROP TABLE IF EXISTS sample_info")
            self("CREATE TABLE sample_info (`n.samples` INTEGER)")

        def __call__(self, sql, args=None):
            c = self.connection.cursor()
            if args:
                c.execute(sql, args)
            else:
                c.execute(sql)

        def close(self):
            self.connection.commit()

        def insert_row(self, row):
            self("INSERT INTO sample_info VALUES(?)", (row['n_samples'],))

    for source_file in source_files(os.path.join(SOURCE_DIR, SAMPLE_INFO_DIR), SAMPLE_INFO_INCLUDE_CLAUSE):
        print "Processing %s..."%source_file
        meta_db = MetaDB(source_file=source_file)
        for row in data_rows_in(source_file):
            meta_db.insert_row(row)
        meta_db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Create a model database from input files.')

    parser.add_argument("--input_folder",
                        help="Folder containing -allBetas-, -allResults-, and -allLogs- input data",
                        default="input")

    parser.add_argument("--results_sub_folder",
                        help="Subfolder with -allResults-",
                        default="allResults")

    parser.add_argument("--betas_sub_folder",
                        help="Subfolder with -allBetas-",
                        default="allBetas")

    parser.add_argument("--logs_sub_folder",
                        help="Subfolder with -allLogs-",
                        default="allLogs")

    parser.add_argument("--meta-data_sub_folder",
                        help="Subfolder with -allMetaData",
                        default="allMetaData")

    parser.add_argument("--output_folder",
                        help="higher level output folder",
                        default="output")

    parser.add_argument("--betas_include_clause",
                        help="Pattern for betas file name to adhere to",
                        default=".allBetas.")

    parser.add_argument("--results_include_clause",
                        help="Pattern for results file name to adhere to",
                        default=".allResults.")

    parser.add_argument("--logs_include_clause",
                        help="Pattern for logs file name to adhere to",
                        default=".allLogs.")

    parser.add_argument("--sample_info_include_clause",
                        help="Pattern for meta data file name to adhere to",
                        default=".allMetaData.")

    args = parser.parse_args()
    SOURCE_DIR = args.input_folder
    RESULTS_DIR = args.results_sub_folder
    BETAS_DIR = args.betas_sub_folder
    LOGS_DIR = args.logs_sub_folder
    TARGET_DIR = args.output_folder
    BETAS_INCLUDE_CLAUSE = args.betas_include_clause
    RESULTS_INCLUDE_CLAUSE = args.results_include_clause
    LOGS_INCLUDE_CLAUSE = args.logs_include_clause

    generate_weights_file()
    add_extra_data()
    add_log_data()
    add_sample_data()
