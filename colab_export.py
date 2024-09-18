"""
Dumped from Colab. Won't run from command line.
"""

# Run on TensorFlow 2.x
%tensorflow_version 2.x
from __future__ import absolute_import, division, print_function, unicode_literals

#Import relevant modules
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import regularizers

# The following lines adjust the granularity of reporting.
pd.options.display.max_rows = 10
pd.options.display.float_format = "{:.1f}".format

print("Imported modules.")
####
from google.colab import files

uploaded = files.upload()

for fn in uploaded.keys():
    print('User uploaded file "{name}" with length {length} bytes'.format(
        name=fn, length=len(uploaded[fn])))
####
dataset = pd.read_csv(filepath_or_buffer="dataset_small.csv")
####
y_dataset = dataset.iloc[:,-1]
X_dataset = dataset.iloc[:, 0:-1]
print("Dataset separated.")
####
X_dataset_mean = X_dataset.mean()
X_dataset_std = X_dataset.std()
X_dataset_norm = (X_dataset - X_dataset_mean) / X_dataset_std
####
from sklearn.model_selection import train_test_split
X_train_norm, X_test_norm, y_train, y_test = train_test_split(X_dataset, y_dataset, test_size=0.2, random_state=100)
####
y_pred_LR = model_LR.predict(X_test_norm)
####
n_features = X_train_norm.shape[1]
# Create the neural network
model_NN = tf.keras.Sequential([
    layers.Dense(64, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(l2=0.001), input_shape=(n_features,)),
    layers.Dense(32, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(l2=0.001)),
    layers.Dense(16, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(l2=0.001)),
    layers.Dense(1, activation='sigmoid')
])
####
model_NN.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model_NN.fit(X_train_norm, y_train, epochs=200, batch_size=30)
####
model_NN.evaluate(X_test_norm, y_test)
model_NN.evaluate(X_train_norm, y_train)
####
input = X_test_norm.loc[X_test_norm.index[1]]
print(input)

phish_probability = model_NN.predict(np.array([input]))[0][0]
print(f"Phish!" if phish_probability > 0.5 else "Not phish!", f"(probability={phish_probability:.3f})")
