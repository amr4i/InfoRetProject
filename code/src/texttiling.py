#!/usr/bin/python

# *****************************************************************************
#
# Authors: Dianna Hu, Stella Pantela, Jonathan Miller, and Kevin Mu
# Class: Computer Science 187
# Date: December 1, 2014
# Final Project - Implementation of the TextTiling Algorithm
#
# Description: This implementation is based on the article by Marti A. Hearst,
# "TextTiling: Segmenting Text into Multi-Paragraph Subtopic Passages".
#
# The algorithm can be broken down into three parts:
# 1. Tokenization
# 2. Lexical Score Determination
#     a) Blocks
#     b) Vocabulary Introduction
# 3. Boundary Identification
#
# Before running, please make sure that nltk is installed and that you download
# the wordnet and stoplist corpuses. See README for instructions.
#
# *****************************************************************************


'''
puts extracted paragraphs in different files in ./results/ 
sub-directory.
'''

from __future__ import division
import re
import sys
import random
import numpy as np
import os
import glob
from math import sqrt
from collections import Counter
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import TextTilingTokenizer

lemmatizer = WordNetLemmatizer()
stop_words = stopwords.words('english')

def tokenize_string(input_str, w):
    '''
    Tokenize a string using the following four steps:
        1) Turn all text into lowercase and split into tokens by
           removing all punctuation except for apostrophes and internal
           hyphens
        2) Remove common words that don't provide much information about
           the content of the text, called "stop words" 
        3) Reduce each token to its morphological root 
           (e.g. "dancing" -> "dance") using nltk's lemmatize function.
        4) Group the lemmatized tokens into groups of size w, which
           represents the pseudo-sentence size.
 
    Args :
        input_str : A string to tokenize
        w: pseudo-sentence size
    Returns:
        A tuple (token_sequences, unique_tokens, paragraph_breaks), where:
            token_sequences: A list of token sequences, each w tokens long.
            unique_tokens: A set of all unique words used in the text.
            paragraph_breaks: A list of indices such that paragraph breaks
                              occur immediately after each index.
    Raises :
        None
    '''
    paragraphs = [s.strip() for s in input_str.splitlines()]
    paragraphs = [s for s in paragraphs if s != ""]
    tokens = []
    paragraph_breaks = []
    token_count = 0
    pat = r"((?:[a-z]+(?:[-'][a-z]+)*))"
    for paragraph in paragraphs:
        pgrph_tokens = re.findall(pat, paragraph)
        tokens.extend(pgrph_tokens)
        token_count += len(pgrph_tokens)
        paragraph_breaks.append(token_count)
    paragraph_breaks = paragraph_breaks[:-1]

    token_sequences = []
    index = 0  
    cnt = Counter() 
    # split tokens into groups of size w
    for i in xrange(len(tokens)):
        cnt[tokens[i]] += 1
        index += 1
        if index % w == 0:
            token_sequences.append(cnt)
            cnt = Counter()
            index = 0

    # remove stop words from each sequence
    for i in xrange(len(token_sequences)):
        token_sequences[i] = [lemmatizer.lemmatize(word) for word in token_sequences[i] if word not in stop_words]
    # lemmatize the words in each sequence
    for i in xrange(len(token_sequences)):
        token_sequences[i] = [lemmatizer.lemmatize(word) for word in token_sequences[i]]
    # get unique tokens
    unique_tokens = [word for word in set(tokens) if word not in stop_words] 

    return (token_sequences, unique_tokens, paragraph_breaks)

def block_score(k, token_seq_ls, unique_tokens):
    """
    Provide similarity scores for adjacent blocks of token sequences.
    Args:
        k: the block size, as defined in the paper (Hearst 1997) 
        token_seq_ls: list of token sequences, each of the same length
        unique_tokens: A set of all unique words used in the text.
    Returns:
        list of block scores from gap k through gap (len(token_seq_ls)-k-2),
        inclusive.
    Raises:
        None.
    """
    score_ls = []
    # calculate score for each gap with at least k token sequences on each side
    for gap_index in range(1, len(token_seq_ls)):
        current_k = min(gap_index, k, len(token_seq_ls) - gap_index)
        before_block = token_seq_ls[gap_index - current_k : gap_index]
        after_block = token_seq_ls[gap_index : gap_index + current_k]
        
        before_cnt = Counter()
        after_cnt = Counter()
        for j in xrange(current_k):
            before_cnt += Counter(token_seq_ls[gap_index + j - current_k])
            after_cnt += Counter(token_seq_ls[gap_index + j])
        
        # calculate and store score
        numerator = 0.0
        before_sq_sum = 0.0
        after_sq_sum = 0.0
        for token in unique_tokens:
            numerator += (before_cnt[token] * after_cnt[token])
            before_sq_sum += (before_cnt[token] ** 2)
            after_sq_sum += (after_cnt[token] ** 2)
        denominator = sqrt(before_sq_sum * after_sq_sum)
        score_ls.append(numerator / denominator)
    return score_ls

def vocabulary_introduction(token_sequences, w):
  """
  Computes lexical score for the gap between pairs of text sequences.
  It starts assigning scores after the first sequence.

  Args:
    w: size of a sequence

  Returns:
    list of scores where scores[i] corresponds to the score at gap position i,
    that is the score after sequence i.

  Raises:
    None
  """
  new_words1 = set()
  new_words2 = set(token_sequences[0])
  w2 = w * 2

  # score[i] corresponds to gap position i
  scores = []
  for i in xrange(1,len(token_sequences)-1):
    # new words to the left of the gap
    new_wordsb1 = set(token_sequences[i-1]).difference(new_words1)

    # new words to the right of the gap
    new_wordsb2 = set(token_sequences[i+1]).difference(new_words2)

    # calculate score and update score array
    score = (len(new_wordsb1) + len(new_wordsb2)) / w2
    scores.append(score)

    # update sets that keep track of new words
    new_words1 = new_words1.union(token_sequences[i-1])
    new_words2 = new_words2.union(token_sequences[i+1])

  # special case on last element
  b1 = len(set(token_sequences[len(token_sequences)-1]).difference(new_words1))
  scores.append(b1/w2)
  return scores

def getDepthCutoff(lexScores, liberal=True):
    """
    Get the cutoff for depth scores, above which gaps are considered boundaries.

    Args:
        lexScores: list of lexical scores for each token-sequence gap
        liberal: True IFF liberal criterion will be used for determining cutoff
    Returns:
        A float representing the depth cutoff score
    Raises:
        None
    """
    mean = np.mean(lexScores)
    stdev = np.std(lexScores)
    return mean - stdev if liberal else mean - stdev / 2

def getDepthSideScore(lexScores, currentGap, left):
    """
    Get the depth score for the specified side of the specified gap

    Args:
        lexScores: list of lexical scores for each token-sequence gap
        currentGap: index of gap for which to get depth side score
        left: True IFF the depth score for left side is desired
    Returns:
        A float representing the depth score for the specified side and gap,
        calculated by finding the "peak" on the side of the gap and returning
        the difference between the lexical scores of the peak and gap.
    Raises:
        None
    """
    depthScore = 0
    i = currentGap

    # continue traversing side while possible to find new peak
    while lexScores[i] - lexScores[currentGap] >= depthScore:
        # update depth score based on new peak
        depthScore = lexScores[i] - lexScores[currentGap]

        # go either left or right depending on specification
        i = i - 1 if left else i + 1

        # do not go beyond bounds of gap!
        if (i < 0 and left) or (i == len(lexScores) and not left):
            break
    return depthScore

def getGapBoundaries(lexScores):
    """
    Get the gaps to be considered as boundaries based on gap lexical scores.

    Args:
        lexScores: list of lexical scores for each token-sequence gap
    Returns:
        A list of gaps (identified by index) that are considered boundaries.
    Raises:
        None
    """
    boundaries = []
    cutoff = getDepthCutoff(lexScores)

    for i, score in enumerate(lexScores):
        # find maximum depth to left and right
        depthLeftScore = getDepthSideScore(lexScores, i, True)
        depthRightScore = getDepthSideScore(lexScores, i, False)

        # add gap to boundaries if depth score beyond threshold
        depthScore = depthLeftScore + depthRightScore
        if depthScore >= cutoff:
            boundaries.append(i)
    return boundaries

def getBoundaries(lexScores, pLocs, w):
    """
    Get locations of paragraphs where subtopic boundaries occur

    Args:
        lexScores: list of lexical scores for each token-sequence gap
        pLocs: list of token indices such that paragraph breaks occur after them
        w: number of tokens to be grouped into each token-sequence
    Returns:
        A sorted list of unique paragraph locations (measured in terms of token
        indices) after which a subtopic boundary occurs.
    Raises:
        None
    """
    # convert boundaries from gap indices to token indices
    gapBoundaries = getGapBoundaries(lexScores)
    tokBoundaries = [w * (gap + 1) for gap in gapBoundaries]

    # do not allow duplicates of boundaries
    parBoundaries = set()

    # convert raw token boundary index to closest index where paragraph occurs
    for i in xrange(len(tokBoundaries)):
        parBoundaries.add(min(pLocs, key=lambda b: abs(b - tokBoundaries[i])))

    return sorted(list(parBoundaries))

def random_breaks(prob, possible_breaks):
    """
    Return a list of subtopic boundaries, chosen randomly.
    
    Args:
        prob: Probability of choosing a given paragraph break to be a subtopic
        boundary.
        possible_breaks: Number of paragraph breaks.
    Returns:
        list of gap indices at which there is a predicted subtopic boundary.
    Raises:
        None.
    """
    breaks= []
    for i in range(1, possible_breaks + 1):
        if random.random() < prob:
            breaks.append(i)
    return breaks

def writeTextTiles(boundaries, pLocs, inputText, filename):
    """
    Get TextTiles in the input text based on paragraph locations and boundaries.

    Args:
        boundaries: list of paragraph locations where subtopic boundaries occur
        pLocs: list of token indices such that paragraph breaks occur after them
        inputText: a string of the initial (unsanitized) text
    Returns:
        A list of indicies of section breaks. Index i will be in this list if
        there is a topic break after the ith paragraph. 
    Raises:
        None
    """
    textTiles = []
    paragraphs = [s.strip() for s in inputText.splitlines()]
    paragraphs = [s for s in paragraphs if s != ""]

    assert len(paragraphs) == len(pLocs) + 1
    splitIndices = [pLocs.index(b) + 1 for b in boundaries]

    # uncomment this if you want the text to actually be written
    
    startIndex = 0

    # append section between subtopic boundaries as new TextTile
    for i in splitIndices:
        textTiles.append(paragraphs[startIndex:i])
        startIndex = i
    # tack on remaining paragraphs in last subtopic
    textTiles.append(paragraphs[startIndex:])
    

    for i, textTile in enumerate(textTiles):
        outfile = "results/"+filename.split("/")[-1].split(".tx")[0] + "_" + str(i) + ".txt"
        with open(outfile, 'w') as f:
            for paragraph in textTile:
                f.write(paragraph + '\n\n')
      
    return splitIndices

def precision_recall(original_breaks, new_breaks):
    """
    Calculate precision and recall metrics.

    Args:
        original_breaks: list of actual boundaries in the text.
        new_breaks: list of predicted boundaries in the text.
    Returns:
        a tuple containing the precision and recall, in that order.
    Raises:
        None.
    """
    # assumes input has the topic changes
    new_breaks_set = set(new_breaks)
    original_breaks_set = set(original_breaks)
    
    precision = recall = 0
    if len(new_breaks_set) > 0:
        precision = len(new_breaks_set.intersection(original_breaks_set)) / len(new_breaks_set)
    if len(original_breaks) > 0:
        recall = len(new_breaks_set.intersection(original_breaks_set)) / len(original_breaks)
    #print "Precision is " + str(precision)
    #print "Recall is " + str(recall)
    return (precision, recall)

def window_diff(true_ls, pred_ls, k, N):
    """
    Calculate the WindowDiff metric as proposed in
    http://people.ischool.berkeley.edu/~hearst/papers/pevzner-01.pdf

    Args:
        true_ls: list of actual boundaries in the text.
        pred_ls: list of predicted boundaries in the text.
        k: length of window as defined in the paper.
        N: total number of possible boundary locations as defined in the paper.
    Returns:
        WindowDiff metric (number between 0 and 1).
    Raises:
        None.
    """
    true_dict = Counter()
    pred_dict = Counter()
    for item in true_ls:
        for index in range(item - k + 1, item + 1):
            true_dict[index] += 1
    for item in pred_ls:
        for index in range(item - k + 1, item + 1):
            pred_dict[index] += 1
    total = 0
    for i in range(0, N - k):
        if true_dict[i] != pred_dict[i]:
            total += 1

    metric = float(total)/float(N - k)
    #print "WindowDiff metric is " + str(metric)
    return metric

def write_results(out, orig_breaks, pred_breaks, num_pgraphs, k):
    """
    A helper function that computes precision/recall and WindowDiff 
    and writes the results to some outfile. The writing is currently
    commented out for the sake of brevity in the results.

    Args:
        out: the file pointer used to write the result
        orig_breaks: list of actual boundaries in the text.
        pred_breaks: list of predicted boundaries in the text.
        num_pgraphs: number of paragraph breaks in the text.
        k: length of window as defined in the paper.
    Returns:
       A tuple containing precision, recall, and WindowDiff metric
       in that order.
    Raises:
        None.
    """    
    precision, recall = precision_recall(orig_breaks, pred_breaks)
    wdiff = window_diff(orig_breaks, pred_breaks, k, num_pgraphs)
    #out.write(str(precision) + "," + str(recall) + "," + str(wdiff) + ",\n")
    return (precision, recall, wdiff)

def run_tests(w, k, directory, name_list):
    """
    Helper function that runs the TextTiling on the entire corpus
    for a given set of parameters w and k, and writes the average 
    statistics to outfile. The corpus is assumed to live in the "articles"
    directory, which must be in the same folder as this python file.

    Args:
        outfile: the name of the output file
        w: pseudo-sentence size.
        k: length of window as defined in the paper.
    Returns:
        None
    Raises:
        None.
    """
    input_files = []
    for name in name_list:
        name = name.split('/')[-1]
        input_files.append(os.path.join(directory, name.strip()))
    
    # print input_files
    counter = 0
    for file in input_files:
        print "processing input " + str(counter) +":"+file+ "..."
        counter += 1
        with open(file, 'r') as f:
            num_breaks = int(f.readline())
            original_section_breaks = []
            for i in xrange(num_breaks):
                original_section_breaks.append(int(f.readline()))
            text = f.read()

            # 1) do our block comparison and 2) vocabulary introduction
            token_sequences, unique_tokens, paragraph_breaks = tokenize_string(text, w)
            # scores1 = block_score(k, token_sequences, unique_tokens)
            scores2 = vocabulary_introduction(token_sequences, w)
            # boundaries1 = getBoundaries(scores1, paragraph_breaks, w)
            boundaries2 = getBoundaries(scores2, paragraph_breaks, w)
            # pred_breaks1 = writeTextTiles(boundaries1, paragraph_breaks, text, file)
            pred_breaks2 = writeTextTiles(boundaries2, paragraph_breaks, text, file)
            
            # 3) do nltk's textTiling
            # ttt = TextTilingTokenizer()
            # tiles = ttt.tokenize(text)
            # pred_breaks3 = []
            # paragraph_count = 0
            # for tile in tiles:
            #     tile = tile.strip()           
            #     paragraph_count += tile.count("\n\n") + 1
            #     pred_breaks3.append(paragraph_count)  

    n = len(input_files)
    
def textTiling(directory, name_list):
    
    # run texttiling for single values of w and k.
    w = 20
    k = 10
    print "w = " + str(w) + ", k = " + str(k)
    run_tests(w, k, directory, name_list)


if __name__ == "__main__":
    if len(argv) != 2 and len(argv) != 3:
        print("\nUsage: python texttiling.py <data_directory> [<names_file>]\n")
        sys.exit(0)
    name_list=[]
    if(len(argv) == 2):
        for name in os.listdir(sys.argv[1]):
            name_list.append(name)
    else:
        with open(sys.argv[2], 'r') as f:
            names=f.readlines()
            names = [w.strip() for w in names]
            for name in names:
                name_list.append(name)
    textTiling(sys.argv[1], name_list)

