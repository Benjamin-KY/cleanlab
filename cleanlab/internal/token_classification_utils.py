# Copyright (C) 2017-2022  Cleanlab Inc.
# This file is part of cleanlab.
#
# cleanlab is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cleanlab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with cleanlab.  If not, see <https://www.gnu.org/licenses/>.

"""
Helper methods used internally in cleanlab.token_classification
"""

import re
import string
import numpy as np
from termcolor import colored
from typing import List, Optional, Callable, Tuple


def get_sentence(words: List[str]) -> str:
    """
    Get sentence formed by a list of words with minor processing for readability

    Parameters
    ----------
    words: List[str]
        list of word-level tokens

    Returns
    ----------
    sentence: string
        sentence formed by list of word-level tokens

    """
    sentence = ""
    for word in words:
        if word not in string.punctuation or word in ["-", "("]:
            word = " " + word
        sentence += word
    sentence = sentence.replace(" '", "'").replace("( ", "(").strip()
    return sentence


def filter_sentence(
    sentences: List[str],
    condition: Optional[Callable[[str], bool]] = None,
) -> Tuple[List[str], List[bool]]:
    """
    Filter sentence based on some condition, and returns filter mask

    Parameters
    ----------
        sentences: List[str]
            list of sentences

        condition: Optional[Callable[[str], bool]]
            sentence filtering condition

    Returns
    ---------
        sentences: List[str]
            list of sentences filtered

        mask: List[bool]
            boolean mask such that `mask[i] == True` if the i'th sentence is included in the
            filtered sentence, otherwise `mask[i] == False`

    """
    if not condition:
        condition = lambda sentence: len(sentence) > 1 and "#" not in sentence
    mask = list(map(condition, sentences))
    sentences = [sentence for m, sentence in zip(mask, sentences) if m]
    return sentences, mask


def process_token(token: str, replace: List[Tuple[str, str]] = [("#", "")]) -> str:
    """
    Replaces special characters in the tokens

    Parameters
    ----------
        token: str
            token which potentially contains special characters

        replace: List[Tuple[str, str]]
            list of tuples `(s1, s2)`, where all occurances of s1 are replaced by s2

    Returns
    ---------
        processed_token: str
            processed token whose special character has been replaced

    Note
    ----
        Only applies to characters in the original input token.
    """
    replace_dict = {re.escape(k): v for (k, v) in replace}
    pattern = "|".join(replace_dict.keys())
    compiled_pattern = re.compile(pattern)
    replacement = lambda match: replace_dict[re.escape(match.group(0))]
    processed_token = compiled_pattern.sub(replacement, token)
    return processed_token


def mapping(entities: List[int], maps: List[int]) -> List[int]:
    """
    Map a list of entities to its corresponding entities

    Parameters
    ----------
        entities: List[int]
            a list of given entities

        maps: List[int]
            a list of mapped entities, such that the i'th indexed token should be mapped to `maps[i]`

    Returns
    ---------
        mapped_entities: List[int]
            a list of mapped entities

    Examples
    --------
        >>> unique_identities = [0, 1, 2, 3, 4]  # ["O", "B-PER", "I-PER", "B-LOC", "I-LOC"]
        >>> maps = [0, 1, 1, 2, 2]  # ["O", "PER", "PER", "LOC", "LOC"]
        >>> mapping(unique_identities, maps)
        [0, 1, 1, 2, 2]  # ["O", "PER", "PER", "LOC", "LOC"]
        >>> mapping([0, 0, 4, 4, 3, 4, 0, 2], maps)
        [0, 0, 2, 2, 2, 2, 0, 1]  # ["O", "O", "LOC", "LOC", "LOC", "LOC", "O", "PER"]
    """
    f = lambda x: maps[x]
    return list(map(f, entities))


def merge_probs(probs: np.ndarray, maps: List[int]) -> np.ndarray:
    """
    Merges model-predictive probabilities with desired mapping

    Parameters
    ----------
        probs:
            np.array of shape `(N, K)`, where N is the number of tokens, and K is the number of classes for the model

        maps: List[int]
            a list of mapped index, such that the probability of the token being in the i'th class is mapped to the
            `maps[i]` index. If `maps[i] == -1`, the i'th column of `probs` is ignored. If `np.any(maps == -1)`, the
            returned probability is re-normalized.

    Returns
    ---------
        probs_merged:
            np.array of shape `(N, K')`, where K' is the number of new classes. Probablities are merged and
            re-normalized if necessary.

    """
    old_classes = probs.shape[1]
    map_size = np.max(maps) + 1
    probs_merged = np.zeros([len(probs), map_size], dtype=probs.dtype.type)

    for i in range(old_classes):
        if maps[i] >= 0:
            probs_merged[:, maps[i]] += probs[:, i]
    if -1 in maps:
        row_sums = probs_merged.sum(axis=1)
        probs_merged /= row_sums[:, np.newaxis]
    return probs_merged


def color_sentence(sentence: str, word: str) -> str:
    """
    Searches for a given token in the sentence and returns the sentence where the given token is colored red

    Parameters
    ----------
        sentence:
            a sentence where the word is searched

        word:
            keyword to find in `sentence`. Assumes the word exists in the sentence.
    Returns
    ---------
        colored_sentence:
            `sentence` where the every occurance of the word is colored red, using `termcolor.colored`

    """
    colored_word = colored(word, "red")
    colored_sentence, number_of_substitions = re.subn(
        r"\b{}\b".format(re.escape(word)), colored_word, sentence
    )
    if number_of_substitions == 0:
        # Use basic string manipulation if regex fails
        colored_sentence = sentence.replace(word, colored_word)
    return colored_sentence
