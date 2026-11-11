import pandas as pd

data = pd.read_csv('synthetic_population_dataset.csv')

data.head()

"""#Data Preprocessing

Handle Missing Values:

* Identify and handle missing values appropriately. Handle imputed data by potentially treating imputed features differently.

Normalize and Scale the Features:

* Normalize numerical features using standardization (mean normalization) Encode categorical features appropriately.

Separate Categorical and Numerical Features:

* Extract and process categorical and numerical features separately.

We don't want to include unnamed or id in pre-processing.
"""

data = data.drop(['Unnamed: 0', 'id'], axis=1)

"""## Feature Selection
to do: remove confidence intervals, only numerical col: cc_disclosed
"""

# Separate numerical and categorical columns
numerical_cols = ['cc_disclosed']

categorical_cols = ['GENDER', 'RACETHN', 'EDUCCAT5', 'DIVISION', 'MARITAL_ACS', 'CHILDRENCAT', # decision: only cluster on demographic features because those are most important for comparison/subgroups
                    'CITIZEN_REC', 'BORN_ACS', 'RELIGCAT', 'AGE_INT']

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
import numpy as np

# Impute missing values
imputer_num = SimpleImputer(strategy='mean')
imputer_cat = SimpleImputer(strategy='most_frequent')

data[numerical_cols] = imputer_num.fit_transform(data[numerical_cols])
data[categorical_cols] = imputer_cat.fit_transform(data[categorical_cols])

# Normalize numerical features
scaler = StandardScaler()
data[numerical_cols] = scaler.fit_transform(data[numerical_cols])

# Encode categorical features
encoder = OneHotEncoder(drop='first', sparse_output=False)
encoded_categorical_data = encoder.fit_transform(data[categorical_cols])
encoded_categorical_df = pd.DataFrame(encoded_categorical_data, columns=encoder.get_feature_names_out(categorical_cols), index=data.index)

# Combine numerical and encoded categorical data
processed_data = pd.concat([data[numerical_cols], encoded_categorical_df], axis=1)

# Display the first few rows of the processed data
processed_data.head()

"""# Feature Reduction using PCA and SVD

Now that we have preprocessed the data, the next step is to reduce the dimensionality of the numerical features using Singular Value Dimension (SVD). SVD helps in reducing the number of features while retaining the most important information.
"""

from sklearn.decomposition import PCA, TruncatedSVD
# PCA for numerical features
# pca = PCA(n_components=2)
# pca_data = pca.fit_transform(data[numerical_cols])
# pca_df = pd.DataFrame(data=pca_data, columns=['PC1', 'PC2'], index=data.index)

# Truncated SVD for categorical features as a fallback
svd = TruncatedSVD(n_components=2)
svd_data = svd.fit_transform(encoded_categorical_df)
svd_df = pd.DataFrame(data=svd_data, columns=['SVD1', 'SVD2'], index=data.index)

"""# Clustering on Features Alone

The primary goal of clustering for this study is to group similar synthetic individuals based on their attributes. This clustering helps to:

### Ensure Uniform Distribution:
* Clustering purely on features ensures that people within each cluster are similar in terms of their attributes. This helps in creating a uniform distribution of similar data points across the clusters.

### Theoretical Basis
* Clear Interpretation: Clusters formed based on attributes alone are easier to interpret, as each cluster represents a group of individuals with similar attribute profiles.

* We are studying harm as how others perceive you. The clusters being based purely on attributes (as in, we don't know uncertainty levels for everyone) can act as a control. We can more easily measure how uncertainty affects harm and perception, especially within clusters, once the surveys are conducted, because we have each cluster as an initial control – we can see how different people with different uncertainty values score as we get the results from the survey.  

* This also allows us to keep clustering more straightforward.
"""

import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# K-means clustering on SVD-reduced categorical data
kmeans_svd = KMeans(n_clusters=14, random_state=42)
svd_clusters = kmeans_svd.fit_predict(svd_df)

# Add cluster labels to the SVD DataFrame
svd_df['Cluster'] = svd_clusters

# Seaborn scatter plot for SVD-reduced categorical data with clusters
plt.figure(figsize=(10, 6))
sns.scatterplot(x='SVD1', y='SVD2', hue='Cluster', palette='viridis', data=svd_df)
plt.title('Clustering on SVD-Reduced Categorical Data')
plt.show()

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# Optimize number of clusters using elbow method and silhouette score for SVD-reduced categorical data
sse_svd = []
silhouette_scores_svd = []
K = range(2, 21)
for k in K:
    kmeans_svd = KMeans(n_clusters=k, random_state=42)
    kmeans_svd.fit(svd_df)
    sse_svd.append(kmeans_svd.inertia_)
    silhouette_scores_svd.append(silhouette_score(svd_df, kmeans_svd.labels_))

# Plot elbow method results for SVD-reduced categorical data
plt.figure(figsize=(10, 6))
plt.plot(K, sse_svd, 'bx-')
plt.xlabel('Number of clusters')
plt.ylabel('SSE')
plt.title('Elbow Method for Optimal Number of Clusters (SVD-reduced categorical data)')
plt.show()

# Plot silhouette scores for SVD-reduced categorical data
plt.figure(figsize=(10, 6))
plt.plot(K, silhouette_scores_svd, 'bx-')
plt.xlabel('Number of clusters')
plt.ylabel('Silhouette Score')
plt.title('Silhouette Scores for Optimal Number of Clusters (SVD-reduced categorical data)')
plt.show()

"""Concatenate svd_df[Clusters] to data"""

data = pd.concat([data, svd_df['Cluster']], axis=1)

data.head()

data.tail()

"""Clusters to csv"""

data.to_csv('clustered_data.csv', index=False)
