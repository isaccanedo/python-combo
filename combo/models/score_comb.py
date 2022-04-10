# -*- coding: utf-8 -*-
"""A collection of combination methods for combining raw scores.
"""
# Author: Yue Zhao <zhaoy@cmu.edu>
# License: BSD 2 clause


import numpy as np
from numpy.random import RandomState
from sklearn.utils import check_array
from sklearn.utils import column_or_1d
# noinspection PyProtectedMember
from sklearn.utils import shuffle
from sklearn.utils.extmath import weighted_mode
from sklearn.utils.random import sample_without_replacement
from numpy.testing import assert_equal
from sklearn.utils.multiclass import check_classification_targets

from pyod.utils.utility import check_parameter


def _aom_moa_helper(mode, scores, n_buckets, method, bootstrap_estimators,
                    random_state):
    """Internal helper function for Average of Maximum (AOM) and
    Maximum of Average (MOA). See :cite:`aggarwal2015theoretical` for details.

    First dividing estimators into subgroups, take the maximum/average score
    as the subgroup score. Finally, take the average/maximum of all subgroup 
    scores.

    Parameters
    ----------
    mode : str
        Define the operation model, either "AOM" or "MOA".

    scores : numpy array of shape (n_samples, n_estimators)
        The score matrix outputted from various estimators.

    n_buckets : int, optional (default=5)
        The number of subgroups to build.

    method : str, optional (default='static')
        {'static', 'dynamic'}, if 'dynamic', build subgroups
        randomly with dynamic bucket size.

    bootstrap_estimators : bool, optional (default=False)
        Whether estimators are drawn with replacement.

    random_state : int, RandomState instance or None, optional (default=None)
        If int, random_state is the seed used by the
        random number generator; If RandomState instance, random_state is
        the random number generator; If None, the random number generator
        is the RandomState instance used by `np.random`.

    Returns
    -------
    combined_scores : Numpy array of shape (n_samples,)
        The combined scores.

    """

    if mode != 'AOM' and mode != 'MOA':
        raise NotImplementedError(
            '{mode} is not implemented'.format(mode=mode))

    scores = check_array(scores)
    # TODO: add one more parameter for max number of estimators
    # use random_state instead
    # for now it is fixed at n_estimators/2
    n_estimators = scores.shape[1]
    check_parameter(n_buckets, 2, n_estimators, include_left=True,
                    include_right=True, param_name='n_buckets')

    scores_buckets = np.zeros([scores.shape[0], n_buckets])

    if method == 'static':

        n_estimators_per_bucket = int(n_estimators / n_buckets)
        if n_estimators % n_buckets != 0:
            raise ValueError('n_estimators / n_buckets has a remainder. Not '
                             'allowed in static mode.')

        if not bootstrap_estimators:
            # shuffle the estimator order
            shuffled_list = shuffle(list(range(0, n_estimators, 1)),
                                    random_state=random_state)

            head = 0
            for i in range(0, n_estimators, n_estimators_per_bucket):
                tail = i + n_estimators_per_bucket
                batch_ind = int(i / n_estimators_per_bucket)
                if mode == 'AOM':
                    scores_buckets[:, batch_ind] = np.max(
                        scores[:, shuffled_list[head:tail]], axis=1)
                else:
                    scores_buckets[:, batch_ind] = np.mean(
                        scores[:, shuffled_list[head:tail]], axis=1)

                # increment index
                head = head + n_estimators_per_bucket
                # noinspection PyUnusedLocal
        else:
            for i in range(n_buckets):
                ind = sample_without_replacement(n_estimators,
                                                 n_estimators_per_bucket,
                                                 random_state=random_state)
                if mode == 'AOM':
                    scores_buckets[:, i] = np.max(scores[:, ind], axis=1)
                else:
                    scores_buckets[:, i] = np.mean(scores[:, ind], axis=1)

    elif method == 'dynamic':  # random bucket size
        for i in range(n_buckets):
            # the number of estimators in a bucket should be 2 - n/2
            max_estimator_per_bucket = RandomState(seed=random_state).randint(
                2, int(n_estimators / 2))
            ind = sample_without_replacement(n_estimators,
                                             max_estimator_per_bucket,
                                             random_state=random_state)
            if mode == 'AOM':
                scores_buckets[:, i] = np.max(scores[:, ind], axis=1)
            else:
                scores_buckets[:, i] = np.mean(scores[:, ind], axis=1)

    else:
        raise NotImplementedError(
            '{method} is not implemented'.format(method=method))

    if mode == 'AOM':
        return np.mean(scores_buckets, axis=1)
    else:
        return np.max(scores_buckets, axis=1)


def aom(scores, n_buckets=5, method='static', bootstrap_estimators=False,
        random_state=None):
    """Average of Maximum - An ensemble method for combining multiple
    estimators. See :cite:`aggarwal2015theoretical` for details.

    First dividing estimators into subgroups, take the maximum score as the
    subgroup score. Finally, take the average of all subgroup scores.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        The score matrix outputted from various estimators

    n_buckets : int, optional (default=5)
        The number of subgroups to build

    method : str, optional (default='static')
        {'static', 'dynamic'}, if 'dynamic', build subgroups
        randomly with dynamic bucket size.

    bootstrap_estimators : bool, optional (default=False)
        Whether estimators are drawn with replacement.

    random_state : int, RandomState instance or None, optional (default=None)
        If int, random_state is the seed used by the
        random number generator; If RandomState instance, random_state is
        the random number generator; If None, the random number generator
        is the RandomState instance used by `np.random`.

    Returns
    -------
    combined_scores : Numpy array of shape (n_samples,)
        The combined scores.

    """
    return _aom_moa_helper('AOM', scores, n_buckets, method,
                           bootstrap_estimators, random_state)


def moa(scores, n_buckets=5, method='static', bootstrap_estimators=False,
        random_state=None):
    """Maximization of Average - An ensemble method for combining multiple
    estimators. See :cite:`aggarwal2015theoretical` for details.

    First dividing estimators into subgroups, take the average score as the
    subgroup score. Finally, take the maximization of all subgroup outlier
    scores.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        The score matrix outputted from various estimators

    n_buckets : int, optional (default=5)
        The number of subgroups to build

    method : str, optional (default='static')
        {'static', 'dynamic'}, if 'dynamic', build subgroups
        randomly with dynamic bucket size.

    bootstrap_estimators : bool, optional (default=False)
        Whether estimators are drawn with replacement.

    random_state : int, RandomState instance or None, optional (default=None)
        If int, random_state is the seed used by the
        random number generator; If RandomState instance, random_state is
        the random number generator; If None, the random number generator
        is the RandomState instance used by `np.random`.

    Returns
    -------
    combined_scores : Numpy array of shape (n_samples,)
        The combined scores.

    """
    return _aom_moa_helper('MOA', scores, n_buckets, method,
                           bootstrap_estimators, random_state)


def average(scores, estimator_weights=None):
    """Combination method to merge the scores from multiple estimators
    by taking the average.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        Score matrix from multiple estimators on the same samples.

    estimator_weights : numpy array of shape (1, n_estimators)
        If specified, using weighted average.

    Returns
    -------
    combined_scores : numpy array of shape (n_samples, )
        The combined scores.

    """
    scores = check_array(scores)

    if estimator_weights is not None:
        if estimator_weights.shape != (1, scores.shape[1]):
            raise ValueError(
                'Bad input shape of estimator_weight: (1, {score_shape}),'
                'and {estimator_weights} received'.format(
                    score_shape=scores.shape[1],
                    estimator_weights=estimator_weights.shape))

        # (d1*w1 + d2*w2 + ...+ dn*wn)/(w1+w2+...+wn)
        # generated weighted scores
        scores = np.sum(np.multiply(scores, estimator_weights),
                        axis=1) / np.sum(estimator_weights)
        return scores.ravel()

    else:
        return np.mean(scores, axis=1).ravel()


def maximization(scores):
    """Combination method to merge the scores from multiple estimators
    by taking the maximum.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        Score matrix from multiple estimators on the same samples.

    Returns
    -------
    combined_scores : numpy array of shape (n_samples, )
        The combined scores.

    """

    scores = check_array(scores)
    return np.max(scores, axis=1).ravel()


def median(scores):
    """Combination method to merge the scores from multiple estimators
    by taking the median.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        Score matrix from multiple estimators on the same samples.

    Returns
    -------
    combined_scores : numpy array of shape (n_samples, )
        The combined scores.

    """

    scores = check_array(scores)
    return np.median(scores, axis=1).ravel()


def majority_vote(scores, n_classes=2, weights=None):
    """Combination method to merge the scores from multiple estimators
    by majority vote.

    Parameters
    ----------
    scores : numpy array of shape (n_samples, n_estimators)
        Score matrix from multiple estimators on the same samples.

    n_classes : int, optional (default=2)
        The number of classes in scores matrix

    weights : numpy array of shape (1, n_estimators)
        If specified, using weighted majority weight.

    Returns
    -------
    combined_scores : numpy array of shape (n_samples, )
        The combined scores.

    """

    scores = check_array(scores)

    # assert only discrete scores are combined with majority vote
    check_classification_targets(scores)

    n_samples, n_estimators = scores.shape[0], scores.shape[1]

    vote_results = np.zeros([n_samples, ])

    if weights is not None:
        assert_equal(scores.shape[1], weights.shape[1])

    # equal weights if not set
    else:
        weights = np.ones([1, n_estimators])

    for i in range(n_samples):
        vote_results[i] = weighted_mode(scores[i, :], weights)[0][0]

    return vote_results.ravel()
