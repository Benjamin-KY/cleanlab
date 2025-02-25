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
Ancillary helper methods used internally throughout this package; mostly related to Confident Learning algorithms.
"""

import numpy as np
import pandas as pd


def remove_noise_from_class(noise_matrix, class_without_noise):
    """A helper function in the setting of PU learning.
    Sets all P(label=class_without_noise|true_label=any_other_class) = 0
    in noise_matrix for pulearning setting, where we have
    generalized the positive class in PU learning to be any
    class of choosing, denoted by class_without_noise.

    Parameters
    ----------
    noise_matrix : np.ndarray of shape (K, K), K = number of classes
        A conditional probability matrix of the form P(label=k_s|true_label=k_y) containing
        the fraction of examples in every class, labeled as every other class.
        Assumes columns of noise_matrix sum to 1.

    class_without_noise : int
        Integer value of the class that has no noise. Traditionally,
        this is 1 (positive) for PU learning."""

    # Number of classes
    K = len(noise_matrix)

    cwn = class_without_noise
    x = np.copy(noise_matrix)

    # Set P( labels = cwn | y != cwn) = 0 (no noise)
    x[cwn, [i for i in range(K) if i != cwn]] = 0.0

    # Normalize columns by increasing diagonal terms
    # Ensures noise_matrix is a valid probability matrix
    for i in range(K):
        x[i][i] = 1 - float(np.sum(x[:, i]) - x[i][i])

    return x


def clip_noise_rates(noise_matrix):
    """Clip all noise rates to proper range [0,1), but
    do not modify the diagonal terms because they are not
    noise rates.

    ASSUMES noise_matrix columns sum to 1.

    Parameters
    ----------
    noise_matrix : np.ndarray of shape (K, K), K = number of classes
        A conditional probability matrix containing the fraction of
        examples in every class, labeled as every other class.
        Diagonal terms are not noise rates, but are consistency P(label=k|true_label=k)
        Assumes columns of noise_matrix sum to 1"""

    def clip_noise_rate_range(noise_rate):
        """Clip noise rate P(label=k'|true_label=k) or P(true_label=k|label=k')
        into proper range [0,1)"""
        return min(max(noise_rate, 0.0), 0.9999)

    # Vectorize clip_noise_rate_range for efficiency with np.ndarrays.
    vectorized_clip = np.vectorize(clip_noise_rate_range)

    # Preserve because diagonal entries are not noise rates.
    diagonal = np.diagonal(noise_matrix)

    # Clip all noise rates (efficiently).
    noise_matrix = vectorized_clip(noise_matrix)

    # Put unmodified diagonal back.
    np.fill_diagonal(noise_matrix, diagonal)

    # Re-normalized noise_matrix so that columns sum to one.
    noise_matrix = noise_matrix / noise_matrix.sum(axis=0)

    return noise_matrix


def clip_values(x, low=0.0, high=1.0, new_sum=None):
    """Clip all values in p to range [low,high].
    Preserves sum of x.

    Parameters
    ----------
    x : np.ndarray
        An array / list of values to be clipped.

    low : float
        values in x greater than 'low' are clipped to this value

    high : float
        values in x greater than 'high' are clipped to this value

    new_sum : float
        normalizes x after clipping to sum to new_sum

    Returns
    -------
    x : np.ndarray
        A list of clipped values, summing to the same sum as x."""

    def clip_range(a, low=low, high=high):
        """Clip a into range [low,high]"""
        return min(max(a, low), high)

    vectorized_clip = np.vectorize(
        clip_range
    )  # Vectorize clip_range for efficiency with np.ndarrays
    prev_sum = sum(x) if new_sum is None else new_sum  # Store previous sum
    x = vectorized_clip(x)  # Clip all values (efficiently)
    x = x * prev_sum / float(sum(x))  # Re-normalized values to sum to previous sum
    return x


def value_counts(x):
    """Returns an np.ndarray of shape (K, 1), with the
    value counts for every unique item in the labels list/array,
    where K is the number of unique entries in labels.

    Why this matters? Here is an example:

    .. code:: python

        x = [np.random.randint(0,100) for i in range(100000)]

    .. code:: ipython3

        %timeit np.bincount(x)
        # Result: 100 loops, best of 3: 3.9 ms per loop

    .. code:: ipython3

        %timeit np.unique(x, return_counts=True)[1]
        # Result: 100 loops, best of 3: 7.47 ms per loop

    Parameters
    ----------
    x : list or np.ndarray (one dimensional)
        A list of discrete objects, like lists or strings, for
        example, class labels 'y' when training a classifier.
        e.g. ["dog","dog","cat"] or [1,2,0,1,1,0,2]"""
    try:
        return x.value_counts()
    except Exception:
        if type(x[0]) is int and (np.array(x) >= 0).all():
            return np.bincount(x)
        else:
            return np.unique(x, return_counts=True)[1]


def round_preserving_sum(iterable):
    """Rounds an iterable of floats while retaining the original summed value.
    The name of each parameter is required. The type and description of each
    parameter is optional, but should be included if not obvious.

    The while loop in this code was adapted from:
    https://github.com/cgdeboer/iteround

    Parameters
    -----------
    iterable : list<float> or np.ndarray<float>
        An iterable of floats

    Returns
    -------
    list<int> or np.ndarray<int>
        The iterable rounded to int, preserving sum."""

    floats = np.asarray(iterable, dtype=float)
    ints = floats.round()
    orig_sum = np.sum(floats).round()
    int_sum = np.sum(ints).round()
    # Adjust the integers so that they sum to orig_sum
    while abs(int_sum - orig_sum) > 1e-6:
        diff = np.round(orig_sum - int_sum)
        increment = -1 if int(diff < 0.0) else 1
        changes = min(int(abs(diff)), len(iterable))
        # Orders indices by difference. Increments # of changes.
        indices = np.argsort(floats - ints)[::-increment][:changes]
        for i in indices:
            ints[i] = ints[i] + increment
        int_sum = np.sum(ints).round()
    return ints.astype(int)


def round_preserving_row_totals(confident_joint):
    """Rounds confident_joint cj to type int
    while preserving the totals of reach row.
    Assumes that cj is a 2D np.ndarray of type float.

    Parameters
    ----------
    confident_joint : 2D np.ndarray<float> of shape (K, K)
        See compute_confident_joint docstring for details.

    Returns
    -------
    confident_joint : 2D np.ndarray<int> of shape (K,K)
        Rounded to int while preserving row totals."""

    return np.apply_along_axis(
        func1d=round_preserving_sum,
        axis=1,
        arr=confident_joint,
    ).astype(int)


def int2onehot(labels):
    """Convert list of lists to a onehot matrix for multi-labels

    Parameters
    ----------
    labels: list of lists of integers
      e.g. [[0,1], [3], [1,2,3], [1], [2]]
      All integers from 0,1,...,K-1 must be represented."""

    from sklearn.preprocessing import MultiLabelBinarizer

    mlb = MultiLabelBinarizer()
    return mlb.fit_transform(labels)


def onehot2int(onehot_matrix):
    """Convert a onehot matrix for multi-labels to a list of lists of ints

    Parameters
    ----------
    onehot_matrix: 2D np.ndarray of 0s and 1s
      A one hot encoded matrix representation of multi-labels.

    Returns
    -------
    labels: list of lists of integers
      e.g. [[0,1], [3], [1,2,3], [1], [2]]
      All integers from 0,1,...,K-1 must be represented."""

    return [list(np.where(row == 1)[0]) for row in onehot_matrix]


def estimate_pu_f1(s, prob_s_eq_1):
    """Computes Claesen's estimate of f1 in the pulearning setting.

    Parameters
    ----------
    s : iterable (list or np.ndarray)
      Binary label (whether each element is labeled or not) in pu learning.

    prob_s_eq_1 : iterable (list or np.ndarray)
      The probability, for each example, whether it has label=1 P(label=1|x)

    Output (float)
    ------
    Claesen's estimate for f1 in the pulearning setting."""

    pred = np.asarray(prob_s_eq_1) >= 0.5
    true_positives = sum((np.asarray(s) == 1) & (np.asarray(pred) == 1))
    all_positives = sum(s)
    recall = true_positives / float(all_positives)
    frac_positive = sum(pred) / float(len(s))
    return recall**2 / (2.0 * frac_positive) if frac_positive != 0 else np.nan


def confusion_matrix(true, pred):
    """Implements a confusion matrix for true labels
    and predicted labels. true and pred MUST BE the same length
    and have the same distinct set of class labels represented.

    Results are identical (and similar computation time) to:
        "sklearn.metrics.confusion_matrix"

    However, this function avoids the dependency on sklearn.

    Parameters
    ----------
    true : np.ndarray 1d
      Contains labels.
      Assumes true and pred contains the same set of distinct labels.

    pred : np.ndarray 1d
      A discrete vector of noisy labels, i.e. some labels may be erroneous.
      *Format requirements*: for dataset with K classes, labels must be in {0,1,...,K-1}.

    Returns
    -------
    confusion_matrix : np.ndarray (2D)
      matrix of confusion counts with true on rows and pred on columns."""

    assert len(true) == len(pred)
    true_classes = np.unique(true)
    pred_classes = np.unique(pred)
    K_true = len(true_classes)  # Number of classes in true
    K_pred = len(pred_classes)  # Number of classes in pred
    map_true = dict(zip(true_classes, range(K_true)))
    map_pred = dict(zip(pred_classes, range(K_pred)))

    result = np.zeros((K_true, K_pred))
    for i in range(len(true)):
        result[map_true[true[i]]][map_pred[pred[i]]] += 1

    return result


def print_square_matrix(
    matrix,
    left_name="s",
    top_name="y",
    title=" A square matrix",
    short_title="s,y",
    round_places=2,
):
    """Pretty prints a matrix.

    Parameters
    ----------
    matrix : np.ndarray
        the matrix to be printed
    left_name : str
        the name of the variable on the left of the matrix
    top_name : str
        the name of the variable on the top of the matrix
    title : str
        Prints this string above the printed square matrix.
    short_title : str
        A short title (6 characters or fewer) like P(labels|y) or P(labels,y).
    round_places : int
        Number of decimals to show for each matrix value."""

    short_title = short_title[:6]
    K = len(matrix)  # Number of classes
    # Make sure matrix is 2d array
    if len(np.shape(matrix)) == 1:
        matrix = np.array([matrix])
    print()
    print(title, "of shape", matrix.shape)
    print(" " + short_title + "".join(["\t" + top_name + "=" + str(i) for i in range(K)]))
    print("\t---" * K)
    for i in range(K):
        entry = "\t".join([str(z) for z in list(matrix.round(round_places)[i, :])])
        print(left_name + "=" + str(i) + " |\t" + entry)
    print("\tTrace(matrix) =", np.round(np.trace(matrix), round_places))
    print()


def print_noise_matrix(noise_matrix, round_places=2):
    """Pretty prints the noise matrix."""
    print_square_matrix(
        noise_matrix,
        title=" Noise Matrix (aka Noisy Channel) P(given_label|true_label)",
        short_title="p(s|y)",
        round_places=round_places,
    )


def print_inverse_noise_matrix(inverse_noise_matrix, round_places=2):
    """Pretty prints the inverse noise matrix."""
    print_square_matrix(
        inverse_noise_matrix,
        left_name="y",
        top_name="s",
        title=" Inverse Noise Matrix P(true_label|given_label)",
        short_title="p(y|s)",
        round_places=round_places,
    )


def print_joint_matrix(joint_matrix, round_places=2):
    """Pretty prints the joint label noise matrix."""
    print_square_matrix(
        joint_matrix,
        title=" Joint Label Noise Distribution Matrix P(given_label, true_label)",
        short_title="p(s,y)",
        round_places=round_places,
    )


def compress_int_array(int_array, num_possible_values):
    """Compresses dtype of np.ndarray<int> if num_possible_values is small enough."""
    try:
        compressed_type = None
        if num_possible_values < np.iinfo(np.dtype("int16")).max:
            compressed_type = "int16"
        elif num_possible_values < np.iinfo(np.dtype("int32")).max:  # pragma: no cover
            compressed_type = "int32"  # pragma: no cover
        if compressed_type is not None:
            int_array = int_array.astype(compressed_type)
        return int_array
    except Exception:  # int_array may not even be numpy array, keep as is then
        return int_array


def train_val_split(X, labels, train_idx, holdout_idx):
    """Splits data into training/validation sets based on given indices"""
    labels_train, labels_holdout = (
        labels[train_idx],
        labels[holdout_idx],
    )  # labels are always np.ndarray
    split_completed = False
    if isinstance(X, (pd.DataFrame, pd.Series)):
        X_train, X_holdout = X.iloc[train_idx], X.iloc[holdout_idx]
        split_completed = True
    if not split_completed:
        try:  # check if X is pytorch Dataset object using lazy import
            import torch

            if isinstance(X, torch.utils.data.Dataset):  # special splitting for pytorch Dataset
                X_train = torch.utils.data.Subset(X, train_idx)
                X_holdout = torch.utils.data.Subset(X, holdout_idx)
                split_completed = True
        except Exception:
            pass
    if not split_completed:
        try:  # check if X is tensorflow Dataset object using lazy import
            import tensorflow

            if isinstance(X, tensorflow.data.Dataset):  # special splitting for tensorflow Dataset
                X_train = extract_indices_tf(X, train_idx, allow_shuffle=True)
                X_holdout = extract_indices_tf(X, holdout_idx, allow_shuffle=False)
                split_completed = True
        except Exception:
            pass
    if not split_completed:
        try:
            X_train, X_holdout = X[train_idx], X[holdout_idx]
        except Exception:
            raise ValueError(
                "Cleanlab cannot split this form of dataset (required for cross-validation). "
                "Try a different data format, "
                "or implement the cross-validation yourself and instead provide out-of-sample `pred_probs`"
            )

    return X_train, X_holdout, labels_train, labels_holdout


def subset_X_y(X, labels, mask):
    """Extracts subset of features/labels where mask is True"""
    labels = subset_labels(labels, mask)
    X = subset_data(X, mask)
    return X, labels


def subset_labels(labels, mask):
    """Extracts subset of labels where mask is True"""
    try:  # filtering labels as if it is array or DataFrame
        return labels[mask]
    except Exception:
        try:  # filtering labels as if it is list
            return [l for idx, l in enumerate(labels) if mask[idx]]
        except Exception:
            raise TypeError("labels must be 1D np.ndarray, list, or pd.Series.")


def subset_data(X, mask):
    """Extracts subset of data examples where mask (np.ndarray) is True"""
    try:
        import torch

        if isinstance(X, torch.utils.data.Dataset):
            mask_idx = np.nonzero(mask)[0]
            return torch.utils.data.Subset(X, mask_idx)
    except Exception:
        pass
    try:
        import tensorflow

        if isinstance(X, tensorflow.data.Dataset):  # special splitting for tensorflow Dataset
            mask_idx = np.nonzero(mask)[0]
            return extract_indices_tf(X, mask_idx, allow_shuffle=True)
    except Exception:
        pass
    try:
        return X[mask]
    except Exception:
        raise TypeError("Data features X must be subsettable with boolean mask array: X[mask]")


def extract_indices_tf(X, idx, allow_shuffle):
    """Extracts subset of tensorflow dataset corresponding to examples at particular indices.

    Args:
      X : ``tensorflow.data.Dataset``

      idx : array_like of integer indices corresponding to examples to keep in the dataset.
        Returns subset of examples in the dataset X that correspond to these indices.

      allow_shuffle : bool
        Whether or not shuffling of this data is allowed (eg. must turn off shuffling for validation data).

    Note: this code only works on Datasets in which:
    * ``shuffle()`` has been called before ``batch()``,
    * no other order-destroying operation (eg. ``repeat()``) has been applied.

    Indices are extracted from the original version of Dataset (before shuffle was called rather than in shuffled order).
    """
    import tensorflow

    idx = np.asarray(idx)
    idx = np.int64(idx)  # needed for Windows (reconsider if necessary in the future)

    og_batch_size = None
    if hasattr(X, "_batch_size"):
        og_batch_size = int(X._batch_size)
        X = X.unbatch()

    unshuffled_X, buffer_size = unshuffle_tensorflow_dataset(X)
    if unshuffled_X is not None:
        X = unshuffled_X

    # Create index,value pairs in the dataset (adds extra indices that werent there before)
    X = X.enumerate()
    keys_tensor = tensorflow.constant(idx)
    vals_tensor = tensorflow.ones_like(keys_tensor)  # Ones will be casted to True
    table = tensorflow.lookup.StaticHashTable(
        tensorflow.lookup.KeyValueTensorInitializer(keys_tensor, vals_tensor), default_value=0
    )  # If index not in table, return 0

    def hash_table_filter(index, value):
        table_value = table.lookup(index)  # 1 if index in arr, else 0
        index_in_arr = tensorflow.cast(table_value, tensorflow.bool)  # 1 -> True, 0 -> False
        return index_in_arr

    # Filter the dataset, then drop the added indices
    X_subset = X.filter(hash_table_filter).map(lambda idx, value: value)

    if (unshuffled_X is not None) and allow_shuffle:
        X_subset = X_subset.shuffle(buffer_size=buffer_size)

    if og_batch_size is not None:  # reset batch size to original value
        X_subset = X_subset.batch(og_batch_size)

    return X_subset


def unshuffle_tensorflow_dataset(X):
    """Applies iterative inverse transformations to dataset to get version before ShuffleDataset was created.
    If no ShuffleDataset is in the transformation-history of this dataset, returns None.

    Parameters
    ----------
    X : a tensorflow Dataset that may have been created via series of transformations, one being shuffle.

    Returns
    -------
    Tuple (pre_X, buffer_size) where:
      pre_X : Dataset that was previously transformed to get ShuffleDataset (or None),
      buffer_size : int `buffer_size` previously used in ShuffleDataset,
        or ``len(pre_X)`` if buffer_size cannot be determined, or None if no ShuffleDataset found.
    """
    try:
        import tensorflow
        from tensorflow.python.data.ops.dataset_ops import ShuffleDataset

        X_inputs = [X]
        while len(X_inputs) == 1:
            pre_X = X_inputs[0]
            if isinstance(pre_X, ShuffleDataset):
                buffer_size = len(pre_X)
                if hasattr(pre_X, "_buffer_size"):
                    buffer_size = pre_X._buffer_size.numpy()
                X_inputs = (
                    pre_X._inputs()
                )  # get the dataset that was transformed to create the ShuffleDataset
                if len(X_inputs) == 1:
                    return (X_inputs[0], buffer_size)
            X_inputs = pre_X._inputs()  # returns list of input datasets used to create X
    except Exception:
        pass
    return (None, None)


def is_torch_dataset(X):
    try:
        import torch

        if isinstance(X, torch.utils.data.Dataset):
            return True
    except Exception:
        pass
    return False  # assumes this cannot be torch dataset if torch cannot be imported


def is_tensorflow_dataset(X):
    try:
        import tensorflow

        if isinstance(X, tensorflow.data.Dataset):
            return True
    except Exception:
        pass
    return False  # assumes this cannot be tensorflow dataset if tensorflow cannot be imported


def csr_vstack(a, b):
    """Takes in 2 csr_matrices and appends the second one to the bottom of the first one.
    Alternative to scipy.sparse.vstack. Returns a sparse matrix.
    """
    a.data = np.hstack((a.data, b.data))
    a.indices = np.hstack((a.indices, b.indices))
    a.indptr = np.hstack((a.indptr, (b.indptr + a.nnz)[1:]))
    a._shape = (a.shape[0] + b.shape[0], b.shape[1])
    return a


def append_extra_datapoint(to_data, from_data, index):
    """Appends an extra datapoint to the data object ``to_data``.
    This datapoint is taken from the data object ``from_data`` at the corresponding index.
    One place this could be useful is ensuring no missing classes after train/validation split.
    """
    if not (type(from_data) is type(to_data)):
        raise ValueError("Cannot append datapoint from different type of data object.")

    if isinstance(to_data, np.ndarray):
        return np.vstack([to_data, from_data[index]])
    elif isinstance(from_data, (pd.DataFrame, pd.Series)):
        X_extra = from_data.iloc[[index]]
        to_data = pd.concat([to_data, X_extra])
        return to_data.reset_index(drop=True)
    else:
        try:
            X_extra = from_data[index]
            try:
                return to_data.append(X_extra)
            except Exception:  # special append for sparse matrix
                return csr_vstack(to_data, X_extra)
        except Exception:
            raise TypeError("Data features X must support: X.append(X[i])")


def get_num_classes(labels=None, pred_probs=None, label_matrix=None, multi_label=None):
    """Determines the number of classes based on information considered in a
    canonical ordering. label_matrix can be: noise_matrix, inverse_noise_matrix, confident_joint,
    or any other K x K matrix where K = number of classes.
    """
    if pred_probs is not None:  # pred_probs is number 1 source of truth
        return pred_probs.shape[1]

    if label_matrix is not None:  # matrix dimension is number 2 source of truth
        if label_matrix.shape[0] != label_matrix.shape[1]:
            raise ValueError(f"label matrix must be K x K, not {label_matrix.shape}")
        else:
            return label_matrix.shape[0]

    if labels is None:
        raise ValueError("Cannot determine number of classes from None input")

    return num_unique_classes(labels, multi_label=multi_label)


def num_unique_classes(labels, multi_label=None):
    """Finds the number of unique classes for both single-labeled
    and multi-labeled labels. If multi_label is set to None (default)
    this method will infer if multi_label is True or False based on
    the format of labels.
    This allows for a more general form of multiclass labels that looks
    like this: [1, [1,2], [0], [0, 1], 2, 1]"""
    if multi_label is None:
        multi_label = any(isinstance(l, list) for l in labels)
    if multi_label:
        return len(set(l for grp in labels for l in list(grp)))
    else:
        return len(set(labels))


def smart_display_dataframe(df):  # pragma: no cover
    """Display a pandas dataframe if in a jupyter notebook, otherwise print it to console."""
    try:
        from IPython.display import display

        display(df)
    except Exception:
        print(df)
