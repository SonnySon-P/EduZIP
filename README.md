# An educational Deflate ZIP compressor implementation

I. Project Overview

This GCN-based recommendation system models user–drink interactions as a bipartite graph, employs multi-layer message passing to capture high-order latent relationships between nodes, and leverages vector similarity to accurately predict and recommend items that align with each user’s inferred preferences.

II. Development Environment
- Programming Language: Python
- Editor / IDE: Google Colaboratory

III. Dependencies
- Tenserflow

IV. Suggestions

In the current GCN architecture, because the network dimension is fixed, it is impossible to add new users or new drinks at any time. To add new nodes, GraphSAGE can be used instead. The model can learn the weights and calculate the embedding in real time without retraining the entire graph
