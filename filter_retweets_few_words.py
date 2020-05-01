#!/usr/bin/env python


"""
Code for reading authors' tweets filenames and remove retweets and tweets with
    few words.
The output filtered files are stored in a separate directory.
"""


import argparse
import logging
import os
import sys
import glob
import messages_persistence
import re



if __name__ == '__main__':
    # parsing arguments

    # logging configuration
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s')
    source_dir_data = sys.argv[1]
    dest_dir = sys.argv[2]
    filter_retweets = sys.argv[3]
    min_words = int(sys.argv[4])
    debug = sys.argv[5]

    print "Starting filtering out data ..\n\tsource directory data = {} \n\tdestination directory = {} \n\tfilter retweets = {} \n\tminimal number of words = {} \n\tdebug = {} ".format(str(source_dir_data), str(dest_dir), str(filter_retweets), str(min_words), str(debug))

    print('Creating output directories ...')
    if os.path.exists(dest_dir):
        print(''.join(['Destination directory ', dest_dir, ' already exists. Quitting ...']))
        sys.exit(1)
    os.makedirs(dest_dir)

    print('Processing authors\' files ...')
    #glob module finds all the pathnames matching a pattern
    #glob.glob returns list of pathnames that match given pathname
    filenames = glob.glob(''.join([source_dir_data, os.sep, '*.dat']))
    num_files = len(filenames)              # processing feedback
    i = 0                                   # processing feedback
    retweets_regex_mask = u'(^RT\s)|(?<!\S)RT\s*@[0-9a-zA-Z_]{1,}(?![0-9a-zA-Z_])' # rationale: RT at the beginning of the message or RT followed by a user reference in the middle
    for filename in filenames:
        print(''.join(['\t', str(i), '/', str(num_files), ' files processed\r']))
        i += 1
        print(''.join(['Processing ', filename, ' file ...']))
        messages = messages_persistence.read(filename)
        messages_filtered = []
        for message in messages:
            keep = True
            if filter_retweets and re.search(retweets_regex_mask, message['tweet']):
                keep = False
            if len(message['tweet'].split()) < min_words:
                keep = False
            if keep:
                messages_filtered.append(message)
            else:
                print('Filtering tweet: ' + message['tweet'])

        messages_persistence.write(messages_filtered, 'full', ''.join([dest_dir, os.sep, os.path.basename(filename)]))

    logging.info('Finishing ...RETWEETS PREPROCESSING')
