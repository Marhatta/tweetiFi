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
import random
import sklearn.ensemble
from sklearn import svm
from sklearn.svm import SVC
import copy
import scipy


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



def filter_authors(source_dir_data, threshold):
    selected_filenames = []
    for filename in glob.glob(os.sep.join([source_dir_data, '*'])):
        print("files:{}".format(filename))
        #if threshold <= int(os.path.basename(filename).split('_')[0]):
        selected_filenames.append(filename)
    return selected_filenames



def sample_tweets(authors_list, num_tweets, features):

    print('Function ke andar')
    tweets_sampled = {}
    feature_kind_dict = {}      # Maps each gram (feature) to its kind (gram-4-gram, word-1-gram, pos-1-gram, ...)

    for author in authors_list:
        print('For {}'.format(author))
        #print('For1')
        author_features_list = []
        for feature in features:
            #print('For2')
            #print(author)
            #print(os.sep)
            #print(feature)
            author_features_list.append(sklearn.externals.joblib.load(''.join([author, os.sep, feature, '.pkl'])))
            #print('For2_2')
            for tweet_histogram in author_features_list[-1]:
                #print('For3')
                for gram in tweet_histogram.keys():
                    #print('For4')
                    feature_kind_dict[gram] = feature
                #print('OutFor4')
            #print('OutFor3')
        #print('OutFor2')
        if len(author_features_list) > 0:
            tweets_sampled[author] = list(author_features_list[0])
        for feature in author_features_list[1:]:
            for i in range(len(tweets_sampled[author])):
                tweets_sampled[author][i].update(feature[i])
        tweets_sampled[author] = tweets_sampled[author][0:num_tweets]
    #print('OutFor1')
    return tweets_sampled, feature_kind_dict


def grams_histogram(grams):
    histogram = {}
    for gram in grams:
        if gram in histogram:
            histogram[gram] += 1
        else:
            histogram[gram] = 1
    return histogram

def build_inverse_vocabulary_array(vocabulary):
    inverse_vocabulary_array = numpy.empty(len(vocabulary.keys()), dtype='object')
    for key in vocabulary.keys():
        inverse_vocabulary_array[vocabulary[key]] = key
    return inverse_vocabulary_array


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


def fit_classify(num_trees, x_train, y_train, x_test, y_test):
    rf = sklearn.ensemble.RandomForestClassifier(n_estimators = num_trees, n_jobs = 6)

    #print("x_train:{}".format(x_train))
    #print("y_train:{}".format(y_train))
    #print("x_test:{}".format(manoj))
    #print("y_test:{}".format(y_test))
    rf.fit(x_train, y_train)
    clf = svm.SVC(kernel='linear', C=1.0)
    clf.fit(x_train,y_train)

    # return the fitted model and the accuracy in percentage
    return (rf, rf.predict(x_test),clf.predict(x_test))


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

    # parsing arguments
    #args = command_line_parsing()

    source_dir_data = sys.argv[1]
    dest_dir = sys.argv[2]
    #features = sys.argv[3]
    debug = sys.argv[4]

    #if 'all' in features:
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

    author_dirnames = glob.glob(os.sep.join([source_dir_data, '*.dat']))
    num_files = len(author_dirnames)    # processing feedback
    i = 0                               # processing feedback
    print('Reading dataset and generating n-grams ...')
    for filename in author_dirnames:
        sys.stderr.write(''.join(['\t', str(i), '/', str(num_files), ' files processed\r']))   # processing feedback
        i += 1
        logging.debug(''.join(['Reading tweets and generating n-grams for file ', filename, ' ...']))
        author_dir = os.sep.join([dest_dir, os.path.splitext(os.path.basename(filename))[0]])
        os.makedirs(author_dir)
        ngrams_generator(messages_persistence.read(filename), features, author_dir)

    print('\n')
    print('NgramsOfTestTweetProcessed')

    #args = command_line_parsing()

    # logging configuration
    #logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,format='[%(asctime)s] - %(levelname)s - %(message)s')
    source_dir_data = sys.argv[5]
    output_dir = sys.argv[6]
    min_tweets = int(sys.argv[7])
    test_dir = sys.argv[8]
    repetitions = int(sys.argv[9])
    num_authors = int(sys.argv[10])
    num_tweets = int(sys.argv[11])
    features = sys.argv[12]
    num_trees = int(sys.argv[13])
    num_most_important_features = int(sys.argv[14])
    debug = sys.argv[15]

    if 'all' in features:
        features = features_list

    print(''.join(['Starting the classification ...',
                          '\n\tsource directory data = ', source_dir_data,
                          '\n\toutput directory = ', output_dir,
                          '\n\tminimal number of tweets = ', str(min_tweets),
                          '\n\ttest tweets directory = ', str(test_dir),
                          '\n\tnumber of repetitions = ', str(repetitions),
                          '\n\tnumber of authors = ', str(num_authors),
                          '\n\tnumber of tweets = ', str(num_tweets),
                          '\n\tfeatures = ', str(features),
                          '\n\tnumber of trees = ', str(num_trees),
                          '\n\tnumber of most important features = ', str(num_most_important_features),
                          '\n\tdebug = ', str(debug),
                          ]))

    print('Creating output directory ...')
    if os.path.exists(output_dir):
        print('Output directory already exists. Quitting ...')
        sys.exit(1)
    os.makedirs(output_dir)

    print(''.join(['Filtering out authors with less than ', str(min_tweets), ' tweets ...']))
    authors_list = filter_authors(source_dir_data, min_tweets)
    if len(authors_list) < num_authors:
        print('Too few author\'s filenames to sample. Exiting ...')
        sys.exit(1)
    print(''.join(['Selected ', str(len(authors_list)), ' authors for the experiment.']))
    with open(''.join([output_dir, os.sep, 'filtered_authors.txt']), mode='w') as fd:
        fd.write('\n'.join(authors_list))

    accuracy_accumulator = 0.0

    # the block below are the variables used to account for the final feature kind importance
    # dictionary indexed by the feature kind (char-4-gram, word-1-gram, ...) that contains the sum of the ranks of features of that kind
    feature_kind_importance_accumulator = {}
    for feature in features:
        feature_kind_importance_accumulator[feature] = 0
    # the normalization is the sum of all the ranks from 1 to args.num_most_important_features (arithmetic progression sum) times the number of folds times the number of runs
    feature_importance_normalization = (1.0 + num_most_important_features) * (
                num_most_important_features / 2.0) * repetitions

    for run in range(1, repetitions + 1):
        print('Run ' + str(run))
        run_dir = ''.join([output_dir, os.sep, 'run_', str(run).zfill(3)])
        os.makedirs(run_dir)

        print('\tSampling the authors ...')
        authors_sampled = list(authors_list)  # copy the list
        # random.(authors_sampled)
        authors_sampled = authors_sampled[0:num_authors]
        with open(''.join([run_dir, os.sep, 'sampled_authors.txt']), mode='w') as fd:
            fd.write('\n'.join(authors_sampled))

        print('\tSampling the tweets ...')
        print('Sample tweet ke upar se')
        tweets_sampled, feature_kind_dict = sample_tweets(authors_sampled, num_tweets, features)

        # print("tweets after sampling:{}".format(tweets_sampled))
        fold_tweets_sampled = copy.deepcopy(
            tweets_sampled)  # need to copy recursively all the data so that the hapax legomena step do not interfere in the other folds

        # print("tweets after sampling:{}".format(fold_tweets_sampled))
        # sys.exit(1)
        author_train_start_idx = 0
        class_id = 0
        y_train = [0] * num_authors
        y_test = [0] * 1
        train_list = []
        test_list = []
        #print('\t\tBuilding training/test sets...')
        # print("tweets after sampling:{}".format(fold_tweets_sampled.values()))
        i = 0
        j = 0
        for author in fold_tweets_sampled.keys():
            train_list.append(fold_tweets_sampled[author][0])
            y_train[i] = author
            i = i + 1
            #logging.debug(''.join(['\t\t\tRemoving \'hapax legomena\' for author ', os.path.basename(author), '...']))
            remove_hapax_legomena(train_list[author_train_start_idx:])
            author_train_start_idx += 1

        # print("number of data:{}".format(i))

        print(''.join(['Filtering out authors with less than ', str(min_tweets), ' tweets ...']))
        authors_list = filter_authors(test_dir, min_tweets)
        print("auther list:{}".format(authors_list))
        if len(authors_list) != num_authors:
            print('Too few author\'s filenames to sample. Exiting ...')
            # sys.exit(1)
        print(''.join(['Selected ', str(len(authors_list)), ' authors for the experiment.']))
        with open(''.join([output_dir, os.sep, 'filtered_authors_test.txt']), mode='w') as fd:
            fd.write('\n'.join(authors_list))

        print('\tSampling the authors ...')
        authors_sampled = list(authors_list)  # copy the list
        random.shuffle(authors_sampled)
        authors_sampled = authors_sampled[0:num_authors]
        with open(''.join([run_dir, os.sep, 'sampled_authors_test.txt']), mode='w') as fd:
            fd.write('\n'.join(authors_sampled))

        print('\tSampling the tweets ...')
        tweets_sampled, feature111 = sample_tweets(authors_sampled, num_tweets, features)

        fold_tweets_sampled_test = copy.deepcopy(tweets_sampled)
        print("tweets after sampling:{}".format(tweets_sampled))
        train_list_t = []
        i = 0
        for author in fold_tweets_sampled_test.keys():
            train_list_t.append(fold_tweets_sampled_test[author][0])

        # print("tweets after sampling:{}".format(train_list_t))

        #logging.debug('\t\tFitting and vectorizing the training set ...')
        vectorizer = sklearn.feature_extraction.DictVectorizer()
        x_train = vectorizer.fit_transform(train_list)

        x_test_t = vectorizer.transform(train_list_t)

        # print("X_test array:{}".format(x_test_t))

        # print("X_test array:{}".format(manoj))

        #logging.debug('\t\tTransforming the feature vector in a binary activation feature vector ...')
        x_train = x_train.astype(bool).astype(int)
        x_test = x_test_t.astype(bool).astype(int)

        #logging.debug('\t\tTraining and running the classifier ...')
        #logging.debug(''.join(['\t\tFeature vector training size: ', str(x_train.shape)]))
        model, result, result1 = fit_classify(num_trees, x_train.todense(), y_train, x_test.todense(), y_test)

        print("resultarecoming")
        print("prediction of rf classifier:", result)
        print("prediction of svm classifier:", result1)

        #print('\t\tAccounting for feature importance')
        inverse_vocabulary_array = build_inverse_vocabulary_array(vectorizer.vocabulary_)
        most_important_features_idxs = numpy.argsort(model.feature_importances_)[
                                       -num_most_important_features:]  # the indexes of the 100 most important features in ascending order of importance (the bigger the better)
        for i in range(len(most_important_features_idxs)):  # account the rank of the feature
            feature = inverse_vocabulary_array[most_important_features_idxs[i]]
            feature_kind_importance_accumulator[feature_kind_dict[feature]] += i + 1

        #print('\t\tSaving feature importance data ...')
        sklearn.externals.joblib.dump(vectorizer.vocabulary_,
                                      os.sep.join([output_dir, 'vectorizer_vocabulary.pkl']))
        sklearn.externals.joblib.dump(model.feature_importances_,
                                      os.sep.join([output_dir, 'rf_model_feature_importances.pkl']))

    print('Feature importance:')
    feature_importance_counter = 0.0
    for feature_kind in features:
        feature_importance_counter += feature_kind_importance_accumulator[feature_kind]
    for feature_kind in features:
        logging.info(''.join(['\tFeature ', feature_kind, ' importance: ', str(
            feature_kind_importance_accumulator[feature_kind] / feature_importance_normalization)]))

    print('Finishing ... ;)')
