"""

Model: Long short-term memory (LSTM) with dense (i.e. fully connected) layers
Mehtod: Truncated Backpropagation Through Time (TBPTT)
Architecture: Recurrent Neural Network

Dataset: Monthly sunspots
Task: Multi-step ahead Forecasting of Univariate Time Series (Univariate Regression)

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
from timeit import default_timer as timer

# third-party imports
from keras import backend as K
from keras import optimizers
from keras.callbacks import ModelCheckpoint
from keras.layers import Input, Dense, LSTM
from keras.models import Model
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import tensorflow as tf

# %%


def lstm_dense_sunspots(new_dir=os.getcwd()):
    """
    Main function
    """
    # %%
    # IMPORTS

    os.chdir(new_dir)

    # code repository sub-package imports
    from artificial_neural_networks.code.utils.download_monthly_sunspots import \
        download_monthly_sunspots
    from artificial_neural_networks.code.utils.generic_utils import none_or_int, none_or_float, \
        save_regress_model, series_to_supervised, affine_transformation
    from artificial_neural_networks.code.utils.vis_utils import regression_figs

    # %%
    # SETTINGS
    parser = argparse.ArgumentParser()

    # General settings
    parser.add_argument('--verbose', type=int, default=1)
    parser.add_argument('--reproducible', type=bool, default=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--time_training', type=bool, default=True)
    parser.add_argument('--plot', type=bool, default=True)

    # Settings for preprocessing and hyperparameters
    parser.add_argument('--look_back', type=int, default=20)
    parser.add_argument('--scaling_factor', type=float, default=(1 / 780))
    parser.add_argument('--translation', type=float, default=0)
    parser.add_argument('--layer_size', type=int, default=4)
    parser.add_argument('--n_epochs', type=int, default=3)
    parser.add_argument('--batch_size', type=none_or_int, default=1)
    parser.add_argument('--optimizer', type=str, default='Adam')
    parser.add_argument('--lrearning_rate', type=float, default=1e-3)
    parser.add_argument('--epsilon', type=none_or_float, default=None)
    parser.add_argument('--steps_ahead', type=int, default=20)

    # Settings for saving the model
    parser.add_argument('--save_architecture', type=bool, default=True)
    parser.add_argument('--save_last_weights', type=bool, default=True)
    parser.add_argument('--save_last_model', type=bool, default=True)
    parser.add_argument('--save_models', type=bool, default=False)
    parser.add_argument('--save_weights_only', type=bool, default=False)
    parser.add_argument('--save_best', type=bool, default=True)

    args = parser.parse_args()

    if args.verbose > 0:
        print(args)

    # For reproducibility
    if args.reproducible:
        os.environ['PYTHONHASHSEED'] = '0'
        np.random.seed(args.seed)
        rn.seed(args.seed)
        tf.set_random_seed(args.seed)
        sess = tf.Session(graph=tf.get_default_graph())
        K.set_session(sess)
        # print(hash("keras"))

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

    look_back = args.look_back
    steps_ahead = args.steps_ahead

    train = sunspots[:n_split]
    test = sunspots[n_split - look_back - steps_ahead + 1:]

    train_x, train_y = series_to_supervised(train, look_back, steps_ahead)
    test_x, test_y = series_to_supervised(test, look_back, steps_ahead)

    # %%
    # PREPROCESSING STEP

    scaling_factor = args.scaling_factor
    translation = args.translation

    n_train = train_x.shape[0]  # number of training examples/samples
    n_test = test_x.shape[0]  # number of test examples/samples

    n_in = train_x.shape[1]  # number of features / dimensions
    n_out = train_y.shape[1]  # number of steps ahead to be predicted

    # Reshape training and test sets
    train_x = train_x.reshape(n_train, n_in, 1)
    test_x = test_x.reshape(n_test, n_in, 1)

    # Apply preprocessing
    train_x_ = affine_transformation(train_x, scaling_factor, translation)
    train_y_ = affine_transformation(train_y, scaling_factor, translation)
    test_x_ = affine_transformation(test_x, scaling_factor, translation)
    test_y_ = affine_transformation(test_y, scaling_factor, translation)
    train_ = affine_transformation(train, scaling_factor, translation)
    test_ = affine_transformation(test, scaling_factor, translation)

    # %%
    # Model hyperparameters and ANN Architecture

    x = Input(shape=(n_in, 1))  # input layer
    h = x

    h = LSTM(units=args.layer_size)(h)  # hidden layer

    out = Dense(units=n_out, activation=None)(h)  # output layer

    model = Model(inputs=x, outputs=out)

    if args.verbose > 0:
        model.summary()

    def root_mean_squared_error(y_true, y_pred):
        return K.sqrt(K.mean(K.square(y_pred - y_true), axis=-1))

    loss_function = root_mean_squared_error

    metrics = ['mean_absolute_error', 'mean_absolute_percentage_error']

    lr = args.lrearning_rate
    epsilon = args.epsilon
    optimizer_selection = {
        'Adadelta':
        optimizers.Adadelta(lr=lr, rho=0.95, epsilon=epsilon, decay=0.0),
        'Adagrad':
        optimizers.Adagrad(lr=lr, epsilon=epsilon, decay=0.0),
        'Adam':
        optimizers.Adam(lr=lr, beta_1=0.9, beta_2=0.999, epsilon=epsilon, decay=0.0, amsgrad=False),
        'Adamax':
        optimizers.Adamax(lr=lr, beta_1=0.9, beta_2=0.999, epsilon=epsilon, decay=0.0),
        'Nadam':
        optimizers.Nadam(lr=lr, beta_1=0.9, beta_2=0.999, epsilon=epsilon, schedule_decay=0.004),
        'RMSprop':
        optimizers.RMSprop(lr=lr, rho=0.9, epsilon=epsilon, decay=0.0),
        'SGD':
        optimizers.SGD(lr=lr, momentum=0.0, decay=0.0, nesterov=False)
    }

    optimizer = optimizer_selection[args.optimizer]

    model.compile(optimizer=optimizer, loss=loss_function, metrics=metrics)

    # %%
    # Save trained models for every epoch

    models_path = r'artificial_neural_networks/trained_models/'
    model_name = 'sunspots_lstm_dense'
    weights_path = models_path + model_name + '_weights'
    model_path = models_path + model_name + '_model'
    file_suffix = '_{epoch:04d}_{val_loss:.4f}_{val_mean_absolute_error:.4f}'

    if args.save_weights_only:
        file_path = weights_path
    else:
        file_path = model_path

    file_path += file_suffix

    monitor = 'val_loss'

    if args.save_models:
        checkpoint = ModelCheckpoint(
            file_path + '.h5',
            monitor=monitor,
            verbose=args.verbose,
            save_best_only=args.save_best,
            mode='auto',
            save_weights_only=args.save_weights_only)
        callbacks = [checkpoint]
    else:
        callbacks = []

    # %%
    # TRAINING PHASE

    if args.time_training:
        start = timer()

    model.fit(
        x=train_x_,
        y=train_y_,
        validation_data=(test_x_, test_y_),
        batch_size=args.batch_size,
        epochs=args.n_epochs,
        verbose=args.verbose,
        callbacks=callbacks)

    if args.time_training:
        end = timer()
        duration = end - start
        print('Total time for training (in seconds):')
        print(duration)

    def model_predict(x_, y_series, y_):
        """
        Predict using the LSTM Model (Multi-step ahead Forecasting)
        """
        n_y = y_series.shape[0]

        n_iter = int(np.floor(n_y/steps_ahead))
        L_last_window = n_y % steps_ahead

        y_pred = np.zeros(n_y)

        # Multi-step ahead Forecasting of all the full windows
        for i in range(0, n_iter):
            pred_start = i * steps_ahead
            pred_end = pred_start + steps_ahead
            x_dyn = x_[pred_start:pred_start + 1]
            y_dyn = model.predict(x_dyn)[0]
            y_pred[pred_start:pred_end] = y_dyn

        if L_last_window > 0:
            # Multi-step ahead Forecasting of the last window
            pred_start = n_y - L_last_window
            pred_end = n_y
            x_dyn[0, :, 0] = y_[pred_start - look_back:pred_start]
            y_dyn = model.predict(x_dyn)[0]
            y_pred[pred_start:pred_end] = y_dyn[:L_last_window]

        return y_pred

    # %%
    # TESTING PHASE

    train_y_series = train[look_back:]
    test_y_series = test[look_back+steps_ahead-1:]

    # Predict preprocessed values
    train_y_pred_ = model_predict(train_x_, train_y_series, train_)
    test_y_pred_ = model_predict(test_x_, test_y_series, test_)  # TODO: check

    # Remove preprocessing
    train_y_pred = affine_transformation(train_y_pred_, scaling_factor, translation, inverse=True)
    test_y_pred = affine_transformation(test_y_pred_, scaling_factor, translation, inverse=True)

    train_rmse = sqrt(mean_squared_error(train_y_series, train_y_pred))
    train_mae = mean_absolute_error(train_y_series, train_y_pred)
    train_r2 = r2_score(train_y_series, train_y_pred)

    test_rmse = sqrt(mean_squared_error(test_y_series, test_y_pred))
    test_mae = mean_absolute_error(test_y_series, test_y_pred)
    test_r2 = r2_score(test_y_series, test_y_pred)

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
        regression_figs(train_y=train_y_series, train_y_pred=train_y_pred,
                        test_y=test_y_series, test_y_pred=test_y_pred)

    # %%
    # Save the architecture and the lastly trained model

    save_regress_model(model, models_path, model_name, weights_path, model_path, file_suffix,
                       test_rmse, test_mae, args)

    # %%

    return model


# %%

if __name__ == '__main__':
    model_lstm_dense = lstm_dense_sunspots('../../../../../')