"""

Model: Standard Neural Network (SNN) with dense (i.e. fully connected) layers
Method: Backpropagation
Architecture: Feedforward Neural Network

Dataset: Monthly sunspots
Task: One-step Ahead Forecasting of Univariate Time Series (Univariate Regression)

    Author: Ioannis Kourouklides, www.kourouklides.com
    License:
        https://github.com/kourouklides/artificial_neural_networks/blob/master/LICENSE

"""
# %%
# IMPORTS

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# standard library imports
import argparse
from math import sqrt
import os
import random as rn

# third-party imports
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.tsa.statespace.sarimax import SARIMAX

# %%


def main(new_dir=os.getcwd()):
    """
    Main function
    """
    # %%
    # IMPORTS

    os.chdir(new_dir)

    # code repository sub-package imports
    from artificial_neural_networks.code.utils.download_monthly_sunspots import \
        download_monthly_sunspots
    from artificial_neural_networks.code.utils.generic_utils import affine_transformation

    # %%
    # SETTINGS
    parser = argparse.ArgumentParser()

    # General settings
    parser.add_argument('--verbose', type=int, default=1)
    parser.add_argument('--reproducible', type=bool, default=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--plot', type=bool, default=True)

    # Settings for preprocessing and hyperparameters
    parser.add_argument('--scaling_factor', type=float, default=(1 / 1))
    parser.add_argument('--translation', type=float, default=0)

    args = parser.parse_args()

    if args.verbose > 0:
        print(args)

    # For reproducibility
    if args.reproducible:
        os.environ['PYTHONHASHSEED'] = '0'
        np.random.seed(args.seed)
        rn.seed(args.seed)

    # %%
    # Load the Monthly sunspots dataset

    sunspots_path = download_monthly_sunspots()
    sunspots = np.genfromtxt(
        fname=sunspots_path, dtype=np.float32, delimiter=",", skip_header=1, usecols=1)

    # %%
    # Train-Test split

    n_series = len(sunspots)

    split_ratio = 2 / 3  # between zero and one
    n_split = int(n_series * split_ratio)

    train_y = sunspots[:n_split]
    test_y = sunspots[n_split:]

    # %%
    # PREPROCESSING STEP

    scaling_factor = args.scaling_factor
    translation = args.translation

    n_train = train_y.shape[0]  # number of training examples/samples
    n_test = test_y.shape[0]  # number of test examples/samples

    # Apply preprocessing
    train_y_ = affine_transformation(train_y, scaling_factor, translation)
    test_y_ = affine_transformation(test_y, scaling_factor, translation)

    # %%
    # TRAINING PHASE

    order = (1, 0, 1)
    seasonal_order = (1, 1, 0, 130)
    outlier_exog = np.zeros(n_train)
    model = SARIMAX(train_y_, order=order, seasonal_order=seasonal_order, exog=outlier_exog,
                    enforce_invertibility=False)
    model_fit = model.fit()

    if args.verbose > 0:
        print(model_fit.summary())

    # %%
    # TESTING PHASE

    outlier_exog_fcast = np.zeros((n_test, 1))

    # Predict preprocessed values
    train_y_pred_ = model_fit.predict(start=0, end=n_train-1, exog=outlier_exog_fcast)
    test_y_pred_ = model_fit.predict(start=n_train, end=n_series-1, exog=outlier_exog_fcast)

    # Remove preprocessing
    train_y_pred = affine_transformation(train_y_pred_, scaling_factor, translation, inverse=True)
    test_y_pred = affine_transformation(test_y_pred_, scaling_factor, translation, inverse=True)

    train_rmse = sqrt(mean_squared_error(train_y, train_y_pred))
    train_mae = mean_absolute_error(train_y, train_y_pred)
    train_r2 = r2_score(train_y, train_y_pred)

    test_rmse = sqrt(mean_squared_error(test_y, test_y_pred))
    test_mae = mean_absolute_error(test_y, test_y_pred)
    test_r2 = r2_score(test_y, test_y_pred)

    if args.verbose > 0:
        print('Train RMSE: %.4f ' % (train_rmse))
        print('Train MAE: %.4f ' % (train_mae))
        print('Train (1 - R_squared): %.4f ' % (1.0 - train_r2))
        print('Train R_squared: %.4f ' % (train_r2))
        print('')
        print('Test RMSE: %.4f ' % (test_rmse))
        print('Test MAE: %.4f ' % (test_mae))
        print('Test (1 - R_squared): %.4f ' % (1.0 - test_r2))
        print('Test R_squared: %.4f ' % (test_r2))

    # %%
    # Data Visualization

    if args.plot:
        plt.figure()
        plt.plot(train_y)
        plt.plot(train_y_pred)
        plt.title('Time Series of the training set')
        plt.show()

        plt.figure()
        plt.plot(test_y)
        plt.plot(test_y_pred)
        plt.title('Time Series of the test set')
        plt.show()

        train_errors = train_y - train_y_pred
        plt.figure()
        plt.hist(train_errors, bins='auto')
        plt.title('Histogram of training errors')
        plt.show()

        test_errors = test_y - test_y_pred
        plt.figure()
        plt.hist(test_errors, bins='auto')
        plt.title('Histogram of test errors')
        plt.show()

        plt.figure()
        plt.scatter(x=train_y, y=train_y_pred, edgecolors=(0, 0, 0))
        plt.plot([train_y.min(), train_y.max()], [train_y.min(), train_y.max()], 'k--', lw=4)
        plt.title('Predicted vs Actual for training set')
        plt.show()

        plt.figure()
        plt.scatter(x=test_y, y=test_y_pred, edgecolors=(0, 0, 0))
        plt.plot([test_y.min(), test_y.max()], [test_y.min(), test_y.max()], 'k--', lw=4)
        plt.title('Predicted vs Actual for test set')
        plt.show()

        plt.figure()
        plt.scatter(x=train_y_pred, y=train_errors, edgecolors=(0, 0, 0))
        plt.plot([train_y.min(), train_y.max()], [0, 0], 'k--', lw=4)
        plt.title('Residuals vs Predicted for training set')
        plt.show()

        plt.figure()
        plt.scatter(x=test_y_pred, y=test_errors, edgecolors=(0, 0, 0))
        plt.plot([test_y.min(), test_y.max()], [0, 0], 'k--', lw=4)
        plt.title('Residuals vs Predicted for test set')
        plt.show()


# %%


if __name__ == '__main__':
    main('../../../../../')