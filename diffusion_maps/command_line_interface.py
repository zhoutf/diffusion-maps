#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK                                -*- mode: python -*-

"""Command line interface for the computation of diffusion maps.

"""

import argparse
try:
    import argcomplete
except ImportError:
    argcomplete = None
import logging
import os
import sys

import numpy as np

import diffusion_maps.default as default
import diffusion_maps.version as version
from diffusion_maps import downsample, DiffusionMaps
from diffusion_maps.profiler import Profiler
from diffusion_maps.plot import plot_eigenvectors


def output_eigenvalues(ew: np.array) -> None:
    """Output the table of eigenvalues.

    """
    logging.info('List of eigenvalues:')
    fields = ['Real part', 'Imaginary part']
    fmt = '{:>12} | {:<21}'
    logging.info('-' * 30)
    logging.info(fmt.format(*fields))
    logging.info('-' * 30)
    fmt = '{:+2.9f} | {:+2.9f}'
    for eigenvalue in ew:
        logging.info(fmt.format(eigenvalue.real, eigenvalue.imag))


def use_cuda(args: argparse.Namespace) -> bool:
    """Determine whether to use GPU-accelerated code or not.

    """
    try:
        import pycuda           # noqa
        use_cuda = True and not args.no_gpu
    except ImportError:
        use_cuda = False

    return use_cuda


def main():
    parser = argparse.ArgumentParser(description='Diffusion maps')
    parser.add_argument('data_file', metavar='FILE', type=str,
                        help='process %(metavar)s (should be in NPY format)')
    parser.add_argument('epsilon', metavar='VALUE', type=float,
                        help='kernel bandwidth')
    parser.add_argument('-n', '--num-samples', type=float, metavar='NUM',
                        required=False, help='number of data points to use')
    parser.add_argument('-e', '--num-eigenpairs', type=int, metavar='NUM',
                        required=False, default=default.num_eigenpairs,
                        help='number of eigenvalue/eigenvector pairs to '
                        'compute')
    parser.add_argument('-c', '--cut-off', type=float, required=False,
                        metavar='DISTANCE', help='cut-off to use to enforce '
                        'sparsity in the diffusion maps computation.')
    parser.add_argument('-o', '--output-data', type=str, required=False,
                        default='actual-data.npy', metavar='FILE', help='save '
                        'actual data used in computation to %(metavar)s')
    parser.add_argument('-w', '--eigenvalues', type=str,
                        default='eigenvalues.dat', required=False,
                        metavar='FILE', help='save eigenvalues to '
                        '%(metavar)s')
    parser.add_argument('-v', '--eigenvectors', type=str,
                        default='eigenvectors.npy', required=False,
                        metavar='FILE', help='save eigenvectors to '
                        '%(metavar)s')
    parser.add_argument('-m', '--matrix', type=str, required=False,
                        metavar='FILE', help='save transition matrix to '
                        '%(metavar)s')
    parser.add_argument('-p', '--plot', action='store_true', default=False,
                        help='plot first two eigenvectors')
    parser.add_argument('--no-gpu', action='store_true', required=False,
                        help='disable GPU eigensolver')
    parser.add_argument('--debug', action='store_true', required=False,
                        help='print debugging information')
    parser.add_argument('--profile', required=False, metavar='FILE',
                        type=argparse.FileType('w', encoding='utf-8'),
                        help='run under profiler and save report to '
                        '%(metavar)s')

    args = parser.parse_args(sys.argv[1:])

    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    prog_name = os.path.basename(sys.argv[0])
    logging.info('{} {}'.format(prog_name, version.v_long))
    logging.info('')
    logging.info('Reading data from {!r}...'.format(args.data_file))

    orig_data = np.load(args.data_file)
    if args.num_samples:
        data = downsample(orig_data, int(args.num_samples))
    else:
        data = orig_data

    logging.info('Computing {} diffusion maps with epsilon = {:g} '
                 'on {} data points...'
                 .format(args.num_eigenpairs-1, args.epsilon, data.shape[0]))

    with Profiler(args.profile):
        dm = DiffusionMaps(data, args.epsilon,
                           num_eigenpairs=args.num_eigenpairs,
                           use_cuda=use_cuda(args))

    if args.profile:
        args.profile.close()

    output_eigenvalues(dm.eigenvalues)

    if args.matrix:
        logging.info('Saving transition matrix to {!r}'
                     .format(args.matrix))
        import scipy.io
        scipy.io.mmwrite(args.matrix, dm.kernel_matrix)

    if args.eigenvalues:
        logging.info('Saving eigenvalues to {!r}'
                     .format(args.eigenvalues))
        np.savetxt(args.eigenvalues, dm.eigenvalues)

    if args.eigenvectors:
        logging.info('Saving eigenvectors to {!r}'
                     .format(args.eigenvectors))
        np.save(args.eigenvectors, dm.eigenvectors)

    if args.output_data and args.num_samples:
        logging.info('Saving downsampled data to {!r}'
                     .format(args.output_data))
        np.save(args.output_data, data)

    if args.plot is True:
        plot_eigenvectors(data, dm.eigenvectors)


if __name__ == '__main__':
    main()