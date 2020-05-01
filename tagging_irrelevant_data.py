#!/usr/bin/env python


"""
Code for tagging irrelevant data as numbers, dates, times, URLs, hashtags and
    user references.
The output files are a copy of the input files with the tagging applied.
"""


import argparse
import logging
import os
import sys
import glob
import codecs
import re
import messages_persistence
import itertools


def tag_url(text):
    # source: http://stackoverflow.com/questions/6883049/regex-to-find-urls-in-string-in-python
    # test: import re; re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+' , u'URL', 'ahttp:/www.uol.com.br ahttp://www.uol.com.br https://255.255.255.255/teste http://www.255.1.com/outroteste a a a ')
    #return re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+' , u'URL', text)

    # Thiago Cavalcante's approach
    return re.sub('((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)', u'URL', text)


def tag_userref(text):
    # rational: a username must start with a '@' and have unlimited occurences of letters, numbers and underscores.
    # test: import re; re.sub('(?<!\S)@[0-9a-zA-Z_]{1,}(?![0-9a-zA-Z_])', u'REF', '@user @us3r @1user @1234567890123456 @_0334 @vser @_ @1 @faeeeec-cas caece ce ce asdcc@notuser ewdede-@dqwec email@some.com.br @ @aaa')
    #return re.sub('(?<!\S)@[0-9a-zA-Z_]{1,}(?![0-9a-zA-Z_])', u'REF', text)

    # Thiago Cavalcante's approach
    return re.sub('@[^\s]+', u'REF', text)


def tag_hashtag(text):
    # rationale: https://support.twitter.com/articles/49309
    # test: import re; re.sub('(?<!\S)(#[0-9a-zA-Z_-]+)(?![0-9a-zA-Z_-])', u'TAG', '#anotherhash #123 #a123 a not#hash #[]aaa #avbjd')
    #return re.sub('(?<!\S)(#[0-9a-zA-Z_-]+)(?![0-9a-zA-Z_-])', u'TAG', text)

    # Thiago Cavalcante's approach
    return re.sub('#[a-zA-Z]+', u'TAG', text)


def tag_date(text):
    # rationale: a date is a two or three blocks of digits separated by a slash.
    # test: import re; re.sub(('(?<!\S)('
    #                                       '[0-3]?[0-9]\s?[/-]\s?[0-3]?[0-9]\s?[/-]\s?[0-9]{1,4}|'     # DD/MM/YYYY or MM/DD/YYYY
    #                                       '[0-1]?[0-9]\s?[/-]\s?[0-9]{1,4}|'                          # MM/YYYY
    #                                       '[0-9]{1,4}\s?[/-]\s?[0-1]?[0-9]|'                          # YYYY/MM
    #                                       '[0-3]?[0-9]\s?[/-]\s?[0-3]?[0-9]'                          # DD/MM or MM/DD
    #                       '            )(?![0-9a-zA-Z])'
    #                           ), u'DAT', '23/12/1977 12 - 23- 2014 25-10 12 / 23 09/2013 1999 - 02 90/12 a12/94 12/31. 12/31a 12-31')
    #return re.sub(('(?<!\S)('
    #                            '[0-3]?[0-9]\s?[/-]\s?[0-3]?[0-9]\s?[/-]\s?[0-9]{1,4}|'     # DD/MM/YYYY or MM/DD/YYYY
    #                            '[0-1]?[0-9]\s?[/-]\s?[0-9]{1,4}|'                          # MM/YYYY
    #                            '[0-9]{1,4}\s?[/-]\s?[0-1]?[0-9]|'                          # YYYY/MM
    #                            '[0-3]?[0-9]\s?[/-]\s?[0-3]?[0-9]'                          # DD/MM or MM/DD
    #                       ')(?![0-9a-zA-Z])'
    #               ), u'DAT', text)

    # Thiago Cavalcante's approach
    return re.sub('[0-9]?[0-9][-/][0-9]?[0-9]([-/][0-9][0-9][0-9][0-9])?', u'DAT', text)


def tag_time(text):
    # rationale: a time is one or two digits followed by a colon and one or two more digits followed by an optional seconds block. An optional AM/PM suffix can also occur.
    # test: import re; re.sub('(?<!\S)([0-2]?[0-9]:[0-5]?[0-9](:[0-5]?[0-9])?\s?([A|P]M)?)(?![0-9a-zA-Z])', u'TIM', '00:00 AM 1:01PM 2:2 pm 01:02:03 Am 01:02. 03:12! 03:14a bbb 60:60 3:40am', flags=re.IGNORECASE)
    #return re.sub('(?<!\S)([0-2]?[0-9]:[0-5]?[0-9](:[0-5]?[0-9])?\s?([A|P]M)?)(?![0-9a-zA-Z])', u'TIM', text, flags=re.IGNORECASE)

    # Thiago Cavalcante's approach
    return re.sub('[0-9]?[0-9]:[0-9]?[0-9](:[0-9]?[0-9])?', u'TIM', text)


def tag_number(text):
    # rationale: a number is a group of consecutive digits, comma and points, prefixed by a optional plus/minus. Obs: expected very few false positives
    # test: import re; re.sub('(?<!\S)([+-]?[0-9.,]*[0-9])(?![0-9a-zA-Z+-])', u'NUM', '98.786    123 123.1 345,2 32, 56. .92 ,34 100,000.00 +11,3 -10 10? 10! 1,1..2 1-1 1+1 dadcd12  89hjgj tt.bt.65bnnn 98,3')
    #return re.sub('(?<!\S)([+-]?[0-9.,]*[0-9])(?![0-9a-zA-Z+-])', u'NUM', text)

    # rationale: a number is a group of three possibilities: 1) a leading digits followed by point/comma and optional decimal digits; 2) leading comma/point followed by digits; 3) numbers without comma/point
    # test: import re; re.sub('(?<!\S)([0-9]+[,.][0-9]*|[,.][0-9]+|[0-9]+)(?=\s|$)', u'NUM', '98.786    123 123.1 345,2 32, 56. .92 ,34 dadcd12  89hjgj tt.bt.65bnnn 98,3')
    # return re.sub('(?<!\S)([0-9]+[,.][0-9]*|[,.][0-9]+|[0-9]+)(?=\s|$)', u'NUM', text)

    # Thiago Cavalcante's approach
    return re.sub('[0-9]+', u'NUM', text)


if __name__ == '__main__':
    # parsing arguments
    #args = command_line_parsing()
    source_dir_data = sys.argv[1]
    dest_dir = sys.argv[2]
    no_number = False
    no_date = False
    no_time = False
    no_url = False
    no_hashtag = False
    no_userref = False
    debug = sys.argv[3]
    # logging configuration
    #logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s')

    print(''.join(['Starting tagging data ...',
                           '\n\tsource directory data = ', str(source_dir_data),
                           '\n\tdestination directory = ', str(dest_dir),
                           '\n\ttag numbers = ', str(not no_number),
                           '\n\ttag dates = ', str(not no_date),
                           '\n\ttag times = ', str(not no_time),
                           '\n\ttag URLs= ', str(not no_url),
                           '\n\ttag hashtags = ', str(not no_hashtag),
                           '\n\ttag user references = ', str(not no_userref),
                           '\n\tdebug = ', str(debug),
                         ]))

    print('Creating output directory ...')
    if os.path.exists(dest_dir):
        print('Destination directory already exists. Quitting ...')
        sys.exit(1)
    os.makedirs(dest_dir)

    print('Tagging tweets ...')
    filenames = glob.glob(''.join([source_dir_data, os.sep, '*.dat']))
    i = 0   # processing feedback
    for filename in filenames:
        #sys.stderr.write(''.join(['\t', str(i), '/', str(len(filenames)), ' files processed\r']))   # processing feedback
        i += 1  # processing feedback
        print(''.join(['Processing file ', filename, ' ...']))
        messages = messages_persistence.read(filename)
        messages_tagged = []
        for message in messages:
            tagged = message['tweet']
            if not args.no_url:
                tagged = tag_url(tagged)
            if not args.no_userref:
                tagged = tag_userref(tagged)
            if not args.no_hashtag:
                tagged = tag_hashtag(tagged)
            if not args.no_date:
                tagged = tag_date(tagged)
            if not args.no_time:
                tagged = tag_time(tagged)
            if not args.no_number:
                tagged = tag_number(tagged)
            print('Original message: ' + message['tweet'])
            print('Tagged message: ' + tagged)
            messages_tagged.append(tagged)
        for tagged, message in itertools.izip(messages_tagged, messages):
            if message['pos']:
                message['full'] = u''.join([tagged, u'\n#POS', message['pos'], u'#POS'])
            else:
                message['full'] = tagged
        messages_persistence.write(messages, 'full', os.sep.join([args.dest_dir, os.path.basename(filename)]))

    print('Finishing ...')
