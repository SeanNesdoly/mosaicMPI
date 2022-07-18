import pandas as pd
import numpy as np
import glob
from multiprocessing import Pool, freeze_support
import json
import os
import matplotlib
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
import palettable
from matplotlib.backends.backend_pdf import PdfPages

def create_annotated_heatmaps(
        data, title, metadata=None, metadata_colors=None,
        row_cluster=True, col_cluster=True, row_dendrogram=True, col_dendrogram=True
    ):
    # HAC clustering (compute linkage matrices)
    col_links = linkage(data, method='average', metric='euclidean')
    row_links = linkage(data.T, method='average', metric='euclidean')

    n_columns = data.columns.shape[0]

    fig = plt.figure(figsize=[20, 2 + n_columns/3])
    fig.suptitle(title, fontsize=14)
    gs0 = matplotlib.gridspec.GridSpec(2,2, figure=fig,
                                    height_ratios=[n_columns/3,1], hspace=0.05,
                                    width_ratios=[5,1], wspace=0.05)
    gs1 = matplotlib.gridspec.GridSpecFromSubplotSpec(2,1, subplot_spec=gs0[0],
                                                    height_ratios=[1,8],
                                                    hspace=0)

    # Heatmap
    ax_heatmap = fig.add_subplot(gs1[1])
    ax_col_dendrogram = fig.add_subplot(gs1[0], sharex=ax_heatmap)

    col_dendrogram = dendrogram(col_links, color_threshold=0, ax=ax_col_dendrogram)
    row_dendrogram = dendrogram(row_links, no_plot=True)
    ax_col_dendrogram.set_axis_off()

    xind = col_dendrogram['leaves']
    yind = row_dendrogram['leaves']

    xmin,xmax = ax_col_dendrogram.get_xlim()
    ax_heatmap.imshow(data.iloc[xind,yind].T, aspect='auto', extent=[xmin,xmax,0,1], cmap='YlOrRd', vmin=0, vmax=1)
    ax_heatmap.yaxis.tick_right()
    ax_heatmap.set_yticks((data.columns.astype("int").to_series() - 0.5).div(data.shape[1]))
    ax_heatmap.set_yticklabels(data.columns[yind][::-1])
    ax_heatmap.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
    

    # Annotations
    if metadata is not None:
        # data and metadata must have the same index
        metadata = metadata.loc[data.index]
        #### TODO: implement check that all metadata values have corresponding color values
        missing_data_color = metadata_colors["missing_data"]
    gs2 = matplotlib.gridspec.GridSpecFromSubplotSpec(metadata.shape[1], 1, subplot_spec=gs0[2])
    for i, (track, annot) in enumerate(metadata.iteritems()):
        ax = fig.add_subplot(gs2[i], sharex=ax_heatmap)
        if annot.dtype == "category" or annot.dtype == "object":
            ordered_rgb = annot.iloc[xind].replace(metadata_colors[track])
            if ordered_rgb.isnull().any():
                ordered_rgb = ordered_rgb.cat.add_categories(missing_data_color)
                ordered_rgb = ordered_rgb.fillna(missing_data_color)
            ordered_rgb = ordered_rgb.astype("object").map(matplotlib.colors.to_rgb)
            ordered_rgb = np.array([list(rgb) for rgb in ordered_rgb])
            ax.imshow(np.stack([ordered_rgb, ordered_rgb]), aspect='auto', extent=[xmin,xmax,0,1])
        else:
            ax.imshow(np.stack([annot.iloc[xind],annot.iloc[xind]]), aspect='auto', extent=[xmin,xmax,0,1], cmap='Blues')
        ax.set_yticks([])
        ax.set_ylabel(track, rotation=0, ha='right', va='center')
        if ax.get_subplotspec().is_last_row():
            ax.set_xticklabels(data.index[xind], rotation=90)
        else:
            ax.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
    # Legend
    from matplotlib.patches import Patch
    ax = fig.add_subplot(gs0[1])
    # Add legend
    legend_elements = []
    for track, color_def in metadata_colors.items():
        if track in metadata.columns:
            legend_elements.append(Patch(label=track, facecolor='white', edgecolor=None, ))
            for cat, color in color_def.items():
                if cat in metadata[track].values:
                    legend_elements.append(Patch(label=cat, facecolor=color, edgecolor=None))
            if metadata[track].isnull().any():
                legend_elements.append(Patch(label="Other", facecolor=missing_data_color, edgecolor=None))

    ax.legend(handles=legend_elements, loc='upper left')
    ax.set_axis_off()
    return fig

def plot_annotated_usages(df, metadata, metadata_colors, title, filename):
    samples = df.index.to_series()
    df = df.div(df.sum(axis=1), axis=0)
    annotations = metadata.loc[samples]
    annotations = annotations[[c for c in annotations.columns if c in metadata_colors]]
    fig = create_annotated_heatmaps(data=df, metadata=annotations, metadata_colors=metadata_colors, title=title)
    fig.savefig(filename, transparent=False, bbox_inches = "tight")
    plt.close(fig)  
    return fig