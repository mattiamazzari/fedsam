import numpy as np
import pandas as pd
from baseline_constants import conf
from sklearn.utils import shuffle
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

def label_skew(data,label,K,n_parties,beta,min_require_size = 10):
    """
:param data: Data dataframe
:param label: Label column name
:param K: Number of labels
:param n_parties: Number of parties
:param beta: Dirichlet parameter
:param min_require_size: Minimum data size per point, if below this number, the data will be redistributed to ensure each node has enough data
:return: Split the data to different parties based on the Dirichlet distribution
    """
    y_train = data[label]

    min_size = 0
    partition_all = []
    front = np.array([0])
    N = y_train.shape[0]  # Total number of samples
    # return train_datasets, test_dataset, n_input, number_samples
    split_data = {}

    while min_size < min_require_size:
        idx_batch = [[] for _ in range(n_parties)]
        for k in range(K):
            idx_k = np.where(y_train == k)[0]
            np.random.shuffle(idx_k)
            proportions = np.random.dirichlet(np.repeat(beta, n_parties))
            proportions = np.array([p * (len(idx_j) < N / n_parties) for p, idx_j in zip(proportions, idx_batch)])

            proportions = proportions / proportions.sum()
            proportions = (np.cumsum(proportions) * len(idx_k)).astype(int)[:-1]
            
            back = np.array([idx_k.shape[0]])
            partition =np.concatenate((front,proportions,back),axis=0)
            partition = np.diff(partition) # Calculate the data distribution for each label based on the splitting points
            partition_all.append(partition)
            idx_batch = [idx_j + idx.tolist() for idx_j, idx in zip(idx_batch, np.split(idx_k, proportions))]

            min_size = min([len(idx_j) for idx_j in idx_batch])

    # Split the data based on the indices for each node
    for j in range(n_parties):
        np.random.shuffle(idx_batch[j])
        split_data[j] = data.iloc[idx_batch[j], :]

    return split_data,partition_all


def get_data():

    ### Training data
    train_data = pd.read_csv(conf["train_dataset"])

    train_data,partition_all = label_skew(train_data,conf["label_column"],conf["num_classes"],conf["num_parties"],conf["beta"])
    print("Data distribution for each node:")
    print(partition_all)
    
    train_datasets = {}
    val_datasets = {}
    ## Number of samples for each node
    number_samples = {}

    ## Load datasets, split training data into training and validation sets
    for key in train_data.keys():
        ## Shuffle the data
        train_dataset = shuffle(train_data[key])

        val_dataset = train_dataset[:int(len(train_dataset) * conf["split_ratio"])]
        train_dataset = train_dataset[int(len(train_dataset) * conf["split_ratio"]):]
        train_datasets[key] = train_dataset
        val_datasets[key] = val_dataset

        number_samples[key] = len(train_dataset)

    ## Test set, used to evaluate the model on the Server
    test_dataset = pd.read_csv(conf["test_dataset"])
    test_dataset = test_dataset
    print("Data loading complete!")

    return train_datasets, val_datasets, test_dataset


class FedTSNE:
    def __init__(self, X, random_state: int = 1):
        """
        X: ndarray, shape (n_samples, n_features)
        random_state: int, for reproducible results across multiple function calls.
        """
        self.tsne = TSNE(n_components=2, learning_rate='auto', init='random', random_state=random_state)
        self.X_embedded = self.tsne.fit_transform(X)
        self.colors = np.random.rand(100, 3)

    def visualize(self, y, title=None, save_path='./visualize/tsne.png'):
        assert y.shape[0] == self.X_embedded.shape[0]
        fig, ax = plt.subplots(1, 1)
        ax.scatter(self.X_embedded[:, 0], self.X_embedded[:, 1], c=self.colors[y], s=10)
        ax.set_title(title)
        ax.axis('equal')
        fig.savefig(save_path)
        plt.close(fig)
    
    def visualize_3(self, y_true, y_before, y_after, figsize=None, save_path='./visualize/tsne.png'):
        assert y_true.shape[0] == y_before.shape[0] == y_after.shape[0] == self.X_embedded.shape[0]
        fig, ax = plt.subplots(1, 3, figsize=figsize)
        ax[0].scatter(self.X_embedded[:, 0], self.X_embedded[:, 1], s=2, c=self.colors[y_true])
        ax[1].scatter(self.X_embedded[:, 0], self.X_embedded[:, 1], s=2, c=self.colors[y_before])
        ax[2].scatter(self.X_embedded[:, 0], self.X_embedded[:, 1], s=2, c=self.colors[y_after])
        ax[0].set_title('ground truth')
        ax[1].set_title('before calibration')
        ax[2].set_title('after calibration')
        ax[0].axis('equal')
        ax[1].axis('equal')
        ax[2].axis('equal')
        fig.savefig(save_path)
        plt.close(fig)