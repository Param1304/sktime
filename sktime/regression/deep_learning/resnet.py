"""Residual Network (ResNet) for regression."""

__author__ = ["James-Large", "Withington"]

from copy import deepcopy

from sklearn.utils import check_random_state

from sktime.networks.resnet import ResNetNetwork
from sktime.regression.deep_learning.base import BaseDeepRegressor
from sktime.utils.validation._dependencies import _check_dl_dependencies


class ResNetRegressor(BaseDeepRegressor):
    """Residual Neural Network Regressor adopted from [1].

    Parameters
    ----------
    n_epochs       : int, default = 1500
        the number of epochs to train the model
    batch_size      : int, default = 16
        the number of samples per gradient update.
    random_state    : int or None, default=None
        Seed for random number generation.
    verbose         : boolean, default = False
        whether to output extra information
    loss            : string, default="mean_squared_error"
        fit parameter for the keras model
    optimizer       : keras.optimizer, default=keras.optimizers.Adam(),
    metrics         : list of strings, default=["mean_squared_error"],
    activation      : string or a tf callable, default="linear"
        Activation function used in the output linear layer.
        List of available activation functions:
        https://keras.io/api/layers/activations/
    use_bias        : boolean, default = True
        whether the layer uses a bias vector.
    optimizer       : keras.optimizers object, default = Adam(lr=0.01)
        specify the optimizer and the learning rate to be used.


    Notes
    -----
    Adapted from the implementation from source code
    https://github.com/hfawaz/dl-4-tsc/blob/master/classifiers/resnet.py

    References
    ----------
        .. [1] Wang et. al, Time series classification from
    scratch with deep neural networks: A strong baseline,
    International joint conference on neural networks (IJCNN), 2017.

    Examples
    --------
    >>> from sktime.regression.deep_learning.resnet import ResNetRegressor
    >>> from sktime.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> clf = ResNetRegressor(n_epochs=20, batch_size=4) # doctest: +SKIP
    >>> clf.fit(X_train, Y_train) # doctest: +SKIP
    ResNetRegressor(...)
    """

    _tags = {
        # packaging info
        # --------------
        "authors": ["James-Large", "Withington"],
        "maintainers": ["Withington"],
        "python_dependencies": "tensorflow",
        # estimator type handled by parent class
    }

    def __init__(
        self,
        n_epochs=1500,
        callbacks=None,
        verbose=False,
        loss="mean_squared_error",
        metrics=None,
        batch_size=16,
        random_state=None,
        activation="linear",
        use_bias=True,
        optimizer=None,
    ):
        _check_dl_dependencies(severity="error")
        super().__init__()

        self.n_epochs = n_epochs
        self.callbacks = callbacks
        self.verbose = verbose
        self.loss = loss
        self.metrics = metrics
        self.batch_size = batch_size
        self.random_state = random_state
        self.activation = activation
        self.use_bias = use_bias
        self.optimizer = optimizer
        self.history = None
        self._network = ResNetNetwork(random_state=random_state)

    def build_model(self, input_shape, **kwargs):
        """Construct a compiled, un-trained, keras model that is ready for training.

        In sktime, time series are stored in numpy arrays of shape (d,m), where d
        is the number of dimensions, m is the series length. Keras/tensorflow assume
        data is in shape (m,d). This method also assumes (m,d). Transpose should
        happen in fit.

        Parameters
        ----------
        input_shape : tuple
            The shape of the data fed into the input layer, should be (m,d)

        Returns
        -------
        output : a compiled Keras Model
        """
        import tensorflow as tf
        from tensorflow import keras

        tf.random.set_seed(self.random_state)

        self.optimizer_ = (
            keras.optimizers.Adam(learning_rate=0.01)
            if self.optimizer is None
            else self.optimizer
        )

        if self.metrics is None:
            metrics = [
                "mean_squared_error",
            ]
        else:
            metrics = self.metrics

        input_layer, output_layer = self._network.build_network(input_shape, **kwargs)

        output_layer = keras.layers.Dense(
            units=1, activation=self.activation, use_bias=self.use_bias
        )(output_layer)

        model = keras.models.Model(inputs=input_layer, outputs=output_layer)
        model.compile(
            loss=self.loss,
            optimizer=self.optimizer_,
            metrics=metrics,
        )

        return model

    def _fit(self, X, y):
        """Fit the regressor on the training set (X, y).

        Parameters
        ----------
        X : np.ndarray of shape = (n_instances (n), n_dimensions (d), series_length (m))
            The training input samples.
        y : np.ndarray of shape n
            The training data class labels.

        Returns
        -------
        self : object
        """
        # Transpose to conform to Keras input style.
        X = X.transpose(0, 2, 1)

        check_random_state(self.random_state)
        self.input_shape = X.shape[1:]
        self.model_ = self.build_model(self.input_shape)
        if self.verbose:
            self.model_.summary()

        self.callbacks_ = deepcopy(self.callbacks)
        self.history = self.model_.fit(
            X,
            y,
            batch_size=self.batch_size,
            epochs=self.n_epochs,
            verbose=self.verbose,
            callbacks=self.callbacks_,
        )
        return self

    @classmethod
    def get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            For classifiers, a "default" set of parameters should be provided for
            general testing, and a "results_comparison" set for comparing against
            previously recorded results if the general set does not produce suitable
            probabilities to compare against.

        Returns
        -------
        params : dict or list of dict, default={}
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
            `create_test_instance` uses the first (or only) dictionary in `params`.
        """
        from sktime.utils.validation._dependencies import _check_soft_dependencies

        param1 = {
            "n_epochs": 6,
            "batch_size": 4,
            "use_bias": False,
        }

        param2 = {
            "n_epochs": 4,
            "batch_size": 6,
            "use_bias": True,
        }
        test_params = [param1, param2]

        if _check_soft_dependencies("keras", severity="none"):
            from keras.callbacks import LambdaCallback

            test_params.append(
                {
                    "n_epochs": 2,
                    "callbacks": [LambdaCallback()],
                }
            )

        return test_params
        # serializing lambda functions
    def pickling(lambda_func):
        lf = lambda_func
        #  serialize(lf):
        code = lf.__code__
        env = lf.__globals__
        # Return a picklable representation (e.g., a dictionary)
        return {"code": code, "env": env}
        # returns the constructed dictionary, representing the serialized lambda function
