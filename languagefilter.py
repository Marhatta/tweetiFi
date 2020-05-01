#!/usr/bin/env python


"""
Code for reading authors' tweets filenames and decide which is the
    language based on an API of language detection (guess_language in this
    case). If the language is different from the one specified in the
    --language command-line option, the tweet is not copied to the output file.
The output files are renamed to have the number of tweets selected prefixed in
    their filenames.
"""

import argparse
import sys
import os
import glob
import messages_persistence
import traceback
import logging
import re
import codecs
import itertools
from nltk.util import ngrams
import numpy
import sklearn.feature_extraction
import sklearn.externals.joblib


features_list = ['char-4-gram',
                 'word-1-gram',
                 'word-2-gram',
                 'word-3-gram',
                 'word-4-gram',
                 'word-5-gram',
                 'pos-1-gram',
                 'pos-2-gram',
                 'pos-3-gram',
                 'pos-4-gram',
                 'pos-5-gram',
                ]


def grams_histogram(grams):
    histogram = {}
    for gram in grams:
        if gram in histogram:
            histogram[gram] += 1
        else:
            histogram[gram] = 1
    return histogram


def remove_hapax_legomena(histograms_list):
    if not histograms_list:
        return

    # sum the occurrence of each feature (gram) through numpy operations
    vectorizer = sklearn.feature_extraction.DictVectorizer(sparse=False)
    feature_occurrence_sum = numpy.sum(vectorizer.fit_transform(histograms_list), axis=0)

    # build an array where the elements are the features (grams) in the same order of the feature_occurence_sum columns
    inverse_vocabulary_array = numpy.empty(len(vectorizer.vocabulary_.keys()), dtype='object')
    for gram in vectorizer.vocabulary_.keys():
        inverse_vocabulary_array[vectorizer.vocabulary_[gram]] = gram

    # find the hapax legomena
    hapax_legomena = []
    for i in range(len(feature_occurrence_sum)):
        if feature_occurrence_sum[i] == 1.0:
            hapax_legomena.append(inverse_vocabulary_array[i])

    # remove the hapax legomena
    for hapax in hapax_legomena:
        for histogram in histograms_list:
            if hapax in histogram:
                del histogram[hapax]


def add_postag_id(histogram):
    aux = {}
    postag_id = 1
    for gram in histogram.keys():
        aux[(postag_id, gram)] = histogram[gram]
    return aux


def ngrams_generator(tweets, features, save_dir):
    char_word_len = None
    if 'char-4-gram' in features:
        logging.debug('\tGenerating char-4-gram features ...')
        gram_list = []
        for tweet in tweets:
            grams = ngrams(u' ' + tweet['tweet'] + u' ', 4)  # adding space as delimiter
            gram_list.append(grams_histogram(grams))

        char_word_len = len(gram_list)
        logging.debug('\tRemoving \'hapax legomena\' ...')
        remove_hapax_legomena(gram_list)
        sklearn.externals.joblib.dump(gram_list, os.sep.join([save_dir, 'char-4-gram.pkl']))

    tweets_words = []
    logging.debug('\tRemoving the punctuation of tweets to generate word grams ...')
    punctuation = u'\\!\\"\\#\\$\\%\\&\\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@\\[\\\\\\]\\^\\_\\`\\{\\|\\}\\~'  # source: re.escape(string.punctuation)
    for tweet in tweets:
        words = re.sub(u''.join([u'[', punctuation, u']']), '', tweet['tweet']).split()
        tweets_words.append([u'\x02'] + words + [u'\x03'])  # apply \x02 and \x03 as begin/end identifiers

    for i in range(1, 6):
        if ''.join(['word-', str(i), '-gram']) in features:
            logging.debug(''.join(['\tGenerating word-', str(i), '-gram features ...']))
            gram_list = []
            for tweet in tweets_words:
                if i == 1:
                    grams = ngrams(tweet[1:-1], i)  # do not consider begin/end identifiers in case of word-1-grams
                else:
                    grams = ngrams(tweet, i)
                gram_list.append(grams_histogram(grams))
            if not char_word_len:
                char_word_len = len(gram_list)
            logging.debug('\tRemoving \'hapax legomena\' ...')
            remove_hapax_legomena(gram_list)
            sklearn.externals.joblib.dump(gram_list, ''.join([save_dir, os.sep, 'word-', str(i), '-gram.pkl']))

    tweets_pos = []
    for tweet in tweets:
        if tweet['pos']:
            tweets_pos.append(
                [u'\x02'] + tweet['pos'].split() + [u'\x03'])  # apply \x02 and \x03 as begin/end identifiers
    for i in range(1, 6):
        if ''.join(['pos-', str(i), '-gram']) in features:
            logging.debug(''.join(['\tGenerating pos-', str(i), '-gram features ...']))
            gram_list = []
            for tweet in tweets_pos:
                if i == 1:
                    grams = ngrams(tweet[1:-1], i)  # do not consider begin/end identifiers in case of pos-1-grams
                else:
                    grams = ngrams(tweet, i)
                gram_list.append(add_postag_id(grams_histogram(
                    grams)))  # add an element in the pos-tag gram identifier to not mix up these grams with other char/word grams
            if char_word_len and char_word_len != len(gram_list):
                logging.error(''.join(
                    ['Tweet messages and POS Tags with different sizes for author ', os.path.basename(save_dir), ': ',
                     str(char_word_len), ' and ', str(len(gram_list)), ' respectively. Quitting ...']))
                sys.exit(1)
            logging.debug('\tRemoving \'hapax legomena\' ...')
            remove_hapax_legomena(gram_list)
            sklearn.externals.joblib.dump(gram_list, ''.join([save_dir, os.sep, 'pos-', str(i), '-gram.pkl']))


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
    # parsing argument
    source_dir_data = sys.argv[1]
    dest_dir = sys.argv[2]
    lang_mod_dir = sys.argv[3]
    language = sys.argv[4]
    debug = sys.argv[5]
    # logging configuration

    print("Starting filtering language ... \n\t source directory data = {} \n\t destination directory = {} \n\t language detection module directory = {} \n\t language = {} \n\t debug = {}" .format(source_dir_data, dest_dir, lang_mod_dir, language, str(debug)))

    sys.path.append(lang_mod_dir)
    import guess_language

    print('Creating output directories ...')

    if os.path.exists(dest_dir):
        print(''.join(['Destination directory ', dest_dir, ' already exists. Quitting ...']))
        sys.exit(1)
    os.makedirs(dest_dir)

    languagedetected = 0
    print('Filtering tweets by language ...')
    author_filenames = glob.glob(''.join([source_dir_data, os.sep, '*.dat']))
    print(author_filenames);
    num_files = len(author_filenames)   # processing feedback
    i = 0                               # processing feedback
    for author_filename in author_filenames:
        print(''.join(['\t', str(i), '/', str(num_files), ' files processed\r']))
        i += 1
        print(''.join(['Processing ', author_filename, ' file ...']))
        messages = messages_persistence.read(author_filename)
        messages_filtered = []
        for message in messages:
            print(''.join(['Detecting language for tweet: ', message['tweet']]).encode('utf-8'))
            try:        # code guess-language breaks for some tweets
                detected_language = guess_language.guessLanguageName(message['tweet'])
                languagedetected = languagedetected + 1
            except Exception as e:
                print('guess-language library error in detecting language for tweet: ' + message['tweet'])
                print('Exception message: ' + str(e))
                print('Exception stack trace:')
                traceback.print_tb(sys.exc_info()[2])
                detected_language = None
            if detected_language:
                print(''.join(['\tLanguage \'', detected_language, '\' detected.']))
                if detected_language == language:
                    messages_filtered.append(message)
            else:
                print('No language detected for tweet: ' + message['tweet'])
        destination_filename = ''.join([dest_dir, os.sep, str(len(messages_filtered)).zfill(5), '_', os.path.basename(author_filename)])      # the destination name is the original filename prefixed with the number of tweets
        print(''.join(['Saving ', destination_filename, ' file ...']))
        messages_persistence.write(messages_filtered, 'full', destination_filename)

    print('\n')
    print('Finishing...')
    print(languagedetected)

    #logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s')
    source_dir_data = sys.argv[6]
    dest_dir = sys.argv[7]
    filter_retweets = sys.argv[8]
    min_words = int(sys.argv[9])
    debug = sys.argv[10]

    retweetsfiltered = 0
    print ("Starting filtering out data ..\n\tsource directory data = {} \n\tdestination directory = {} \n\tfilter retweets = {} \n\tminimal number of words = {} \n\tdebug = {} ".format(str(source_dir_data), str(dest_dir), str(filter_retweets), str(min_words), str(debug)))

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
                retweetsfiltered = retweetsfiltered + 1
                print('Filtering tweet: ' + message['tweet'])

        messages_persistence.write(messages_filtered, 'full', ''.join([dest_dir, os.sep, os.path.basename(filename)]))

    print('\n')
    print('RetweetsDone')
    print(retweetsfiltered)

    source_dir_data = sys.argv[11]
    dest_dir = sys.argv[12]
    no_number = False
    no_date = False
    no_time = False
    no_url = False
    no_hashtag = False
    no_userref = False
    debug = sys.argv[13]
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

    taggedTweets = 0
    print('Tagging tweets ...')
    filenames = glob.glob(''.join([source_dir_data, os.sep, '*.dat']))
    i = 0  # processing feedback
    for filename in filenames:
        sys.stderr.write(''.join(['\t', str(i), '/', str(len(filenames)), ' files processed\r']))  # processing feedback
        i += 1  # processing feedback
        logging.debug(''.join(['Processing file ', filename, ' ...']))
        messages = messages_persistence.read(filename)
        messages_tagged = []
        for message in messages:
            tagged = message['tweet']
            if not no_url:
                tagged = tag_url(tagged)
            if not no_userref:
                tagged = tag_userref(tagged)
            if not no_hashtag:
                tagged = tag_hashtag(tagged)
            if not no_date:
                tagged = tag_date(tagged)
            if not no_time:
                tagged = tag_time(tagged)
            if not no_number:
                tagged = tag_number(tagged)
            logging.debug('Original message: ' + message['tweet'])
            taggedTweets = taggedTweets + 1
            logging.debug('Tagged message: ' + tagged)
            messages_tagged.append(tagged)
        for [tagged, message] in itertools.izip(messages_tagged, messages):
            if message['pos']:
                message['full'] = u''.join([tagged, u'\n#POS', message['pos'], u'#POS'])
            else:
                message['full'] = tagged
        messages_persistence.write(messages, 'full', os.sep.join([dest_dir, os.path.basename(filename)]))

    print('\n')
    print('TaggedFinishing')
    print(taggedTweets)

    # parsing arguments
    #args = command_line_parsing()

    source_dir_data = sys.argv[14]
    dest_dir = sys.argv[15]
    features = sys.argv[16]
    debug = sys.argv[17]

    if 'all' in features:
        features = features_list

    # logging configuration
    #logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s')

    print(''.join(['Starting generating n-grams ...',
                           '\n\tsource directory data = ', source_dir_data,
                           '\n\toutput directory = ', dest_dir,
                           '\n\tfeatures = ', str(features),
                           '\n\tdebug = ', str(debug),
                         ]))

    print('Creating output directory ...')
    if os.path.exists(dest_dir):
        print('Output directory already exists. Quitting ...')
        sys.exit(1)
    os.makedirs(dest_dir)

    ngramsGenerated = 0
    author_dirnames = glob.glob(os.sep.join([source_dir_data, '*.dat']))
    num_files = len(author_dirnames)    # processing feedback
    i = 0                               # processing feedback
    print('Reading dataset and generating n-grams ...')
    for filename in author_dirnames:
        sys.stderr.write(''.join(['\t', str(i), '/', str(num_files), ' files processed\r']))   # processing feedback
        i += 1
        logging.debug(''.join(['Reading tweets and generating n-grams for file ', filename, ' ...']))
        ngramsGenerated = ngramsGenerated + 1
        author_dir = os.sep.join([dest_dir, os.path.splitext(os.path.basename(filename))[0]])
        os.makedirs(author_dir)
        ngrams_generator(messages_persistence.read(filename), features, author_dir)

    print('\n')
    print('NGramsFinishing')
    print(ngramsGenerated)
