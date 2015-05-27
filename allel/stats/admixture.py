# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


from allel.model import AlleleCountsArray
from allel.util import asarray_ndim, check_dim0_aligned
from allel.stats.window import moving_statistic


import numpy as np


def h_hat(ac):
    """Unbiased estimator for h, where 2*h is the heterozygosity
    of the population.

    Parameters
    ----------
    ac : array_like, int, shape (n_variants, 2)
        Allele counts array for a single population.

    Returns
    -------
    h_hat : ndarray, float, shape (n_variants,)

    Notes
    -----
    Used in Patterson (2012) for calculation of various statistics.

    """

    # check inputs
    ac = asarray_ndim(ac, 2)
    assert ac.shape[1] == 2, 'only biallelic variants supported'

    # compute allele number
    an = ac.sum(axis=1)

    # compute estimator
    x = (ac[:, 0] * ac[:, 1]) / (an * (an - 1))

    return x


def patterson_f2(aca, acb):
    """Unbiased estimator for F2(A, B), the branch length between populations
    A and B.

    Parameters
    ----------
    aca : array_like, int, shape (n_variants, 2)
        Allele counts for population A.
    acb : array_like, int, shape (n_variants, 2)
        Allele counts for population B.

    Returns
    -------
    f2 : ndarray, float, shape (n_variants,)

    Notes
    -----
    See Patterson (2012), Appendix A.

    """

    # check inputs
    aca = AlleleCountsArray(aca, copy=False)
    assert aca.shape[1] == 2, 'only biallelic variants supported'
    acb = AlleleCountsArray(acb, copy=False)
    assert acb.shape[1] == 2, 'only biallelic variants supported'
    check_dim0_aligned(aca, acb)

    # compute allele numbers
    sa = aca.sum(axis=1)
    sb = acb.sum(axis=1)

    # compute heterozygosities
    ha = h_hat(aca)
    hb = h_hat(acb)

    # compute sample frequencies for the alternate allele
    a = aca.to_frequencies()[:, 1]
    b = acb.to_frequencies()[:, 1]

    # compute estimator
    x = ((a - b) ** 2) - (ha / sa) - (hb / sb)

    return x


# noinspection PyPep8Naming
def patterson_f3(acc, aca, acb):
    """Unbiased estimator for F3(C; A, B), the three-population test for
    admixture in population C.

    Parameters
    ----------
    acc : array_like, int, shape (n_variants, 2)
        Allele counts for the test population (C).
    aca : array_like, int, shape (n_variants, 2)
        Allele counts for the first source population (A).
    acb : array_like, int, shape (n_variants, 2)
        Allele counts for the second source population (B).

    Returns
    -------
    T : ndarray, float, shape (n_variants,)
        Un-normalized f3 estimates per variant.
    B : ndarray, float, shape (n_variants,)
        Estimates for heterozygosity in population C.

    Notes
    -----
    See Patterson (2012), main text and Appendix A.

    For un-normalized f3 statistics, ignore the `B` return value.

    To compute the f3* statistic, which is normalized by heterozygosity in
    population C to remove numerical dependence on the allele frequency
    spectrum, compute ``np.sum(T) / np.sum(B)``.

    """

    # check inputs
    aca = AlleleCountsArray(aca, copy=False)
    assert aca.shape[1] == 2, 'only biallelic variants supported'
    acb = AlleleCountsArray(acb, copy=False)
    assert acb.shape[1] == 2, 'only biallelic variants supported'
    acc = AlleleCountsArray(acc, copy=False)
    assert acc.shape[1] == 2, 'only biallelic variants supported'
    check_dim0_aligned(aca, acb, acc)

    # compute allele number and heterozygosity in test population
    sc = acc.sum(axis=1)
    hc = h_hat(acc)

    # compute sample frequencies for the alternate allele
    a = aca.to_frequencies()[:, 1]
    b = acb.to_frequencies()[:, 1]
    c = acc.to_frequencies()[:, 1]

    # compute estimator
    T = ((c - a) * (c - b)) - (hc / sc)
    B = 2 * hc

    return T, B


def patterson_d(aca, acb, acc, acd):
    """Unbiased estimator for D(A, B; C, D), the normalised four-population
    test for admixture between (A or B) and (C or D), also known as the
    "ABBA BABA" test.

    Parameters
    ----------
    aca : array_like, int, shape (n_variants, 2),
        Allele counts for population A.
    acb : array_like, int, shape (n_variants, 2)
        Allele counts for population B.
    acc : array_like, int, shape (n_variants, 2)
        Allele counts for population C.
    acd : array_like, int, shape (n_variants, 2)
        Allele counts for population D.

    Returns
    -------
    num : ndarray, float, shape (n_variants,)
        Numerator (un-normalised f4 estimates).
    den : ndarray, float, shape (n_variants,)
        Denominator.

    Notes
    -----
    See Patterson (2012), main text and Appendix A.

    For un-normalized f4 statistics, ignore the `den` return value.

    """

    # check inputs
    aca = AlleleCountsArray(aca, copy=False)
    assert aca.shape[1] == 2, 'only biallelic variants supported'
    acb = AlleleCountsArray(acb, copy=False)
    assert acb.shape[1] == 2, 'only biallelic variants supported'
    acc = AlleleCountsArray(acc, copy=False)
    assert acc.shape[1] == 2, 'only biallelic variants supported'
    acd = AlleleCountsArray(acd, copy=False)
    assert acd.shape[1] == 2, 'only biallelic variants supported'
    check_dim0_aligned(aca, acb, acc, acd)

    # compute sample frequencies for the alternate allele
    a = aca.to_frequencies()[:, 1]
    b = acb.to_frequencies()[:, 1]
    c = acc.to_frequencies()[:, 1]
    d = acd.to_frequencies()[:, 1]

    # compute estimator
    num = (a - b) * (c - d)
    den = (a + b - (2 * a * b)) * (c + d - (2 * c * d))

    return num, den


# noinspection PyPep8Naming
def blockwise_patterson_f3(acc, aca, acb, blen, normed=True):
    """TODO

    """

    # calculate per-variant values
    T, B = patterson_f3(acc, aca, acb)

    # N.B., nans can occur if any of the populations have completely missing
    # genotype calls at a variant (i.e., allele number is zero). Here we
    # assume that is rare enough to be negligible.

    if normed:
        T_bsum = moving_statistic(T, statistic=np.nansum, size=blen)
        B_bsum = moving_statistic(B, statistic=np.nansum, size=blen)
        vb = T_bsum / B_bsum
        m, se, vj = jackknife((T_bsum, B_bsum),
                              statistic=lambda t, b: np.sum(t) / np.sum(b))

    else:
        vb = moving_statistic(T, statistic=np.nanmean, size=blen)
        m, se, vj = jackknife(vb, statistic=np.mean)

    z = m / se
    return m, se, z, vb, vj


def blockwise_patterson_d(aca, acb, acc, acd, blen):
    """TODO

    """

    # calculate per-variant values
    num, den = patterson_d(aca, acb, acc, acd)

    # N.B., nans can occur if any of the populations have completely missing
    # genotype calls at a variant (i.e., allele number is zero). Here we
    # assume that is rare enough to be negligible.

    num_bsum = moving_statistic(num, statistic=np.nansum, size=blen)
    den_bsum = moving_statistic(den, statistic=np.nansum, size=blen)
    vb = num_bsum / den_bsum
    m, se, vj = jackknife((num_bsum, den_bsum),
                          statistic=lambda n, d: np.sum(n) / np.sum(d))
    z = m / se
    return m, se, z, vb, vj


def jackknife(values, statistic):

    if isinstance(values, tuple):
        # multiple input arrays
        n = len(values[0])
        masked_values = [np.ma.asarray(v) for v in values]
        for m in masked_values:
            m.mask = np.zeros(m.shape, dtype=bool)
    else:
        n = len(values)
        masked_values = np.ma.asarray(values)
        masked_values.mask = np.zeros(values.shape, dtype=bool)

    vj = list()

    for i in range(n):

        if isinstance(values, tuple):
            # multiple input arrays
            for m in masked_values:
                m.mask[i] = True
            x = statistic(*masked_values)
            for m in masked_values:
                m.mask[i] = False
        else:
            masked_values.mask[i] = True
            x = statistic(masked_values)
            masked_values.mask[i] = False

        vj.append(x)

    vj = np.array(vj)
    m = vj.mean()
    sv = ((n - 1) / n) * np.sum((vj - m) ** 2)
    se = np.sqrt(sv)
    return m, se, vj
