import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import upsetplot
from scipy.cluster.hierarchy import linkage, dendrogram
from anndata import read_h5ad
import networkx as nx
from cnmfsns.sns import get_category_overrepresentation

def annotated_heatmap(
        data, title, metadata=None, metadata_colors=None,
        row_cluster=True, col_cluster=True, plot_col_dendrogram=True, show_sample_labels=True):

    n_columns = data.columns.shape[0]
    if metadata is None:
        n_metadata_columns = 0
    else:
        n_metadata_columns = metadata.shape[1]

    fig = plt.figure(figsize=[20, 2 + n_columns/3 + n_metadata_columns/4])
    fig.suptitle(title, fontsize=14)
    gs0 = matplotlib.gridspec.GridSpec(2,2, figure=fig,
                                    height_ratios=[n_columns/3, 1 + n_metadata_columns/4], hspace=0.05,
                                    width_ratios=[5,1], wspace=0.05)
    
    # subdivide heatmap and dendrogram
    gs1 = matplotlib.gridspec.GridSpecFromSubplotSpec(2,1, subplot_spec=gs0[0],
                                                    height_ratios=[1,n_columns],
                                                    hspace=0)

    # Heatmap
    ax_heatmap = fig.add_subplot(gs1[1])
    ax_col_dendrogram = fig.add_subplot(gs1[0], sharex=ax_heatmap)
    ax_col_dendrogram.set_axis_off()

    # HAC clustering (compute linkage matrices)
    if col_cluster:
        col_links = linkage(data, method='average', metric='euclidean')
        if plot_col_dendrogram:
            col_dendrogram = dendrogram(col_links, color_threshold=0, ax=ax_col_dendrogram)
        else:
            col_dendrogram = dendrogram(col_links, no_plot=True)
        xind = col_dendrogram['leaves']
    else:
        xind = np.arange(0, data.shape[0])
    if row_cluster:
        row_links = linkage(data.T, method='average', metric='euclidean')
        row_dendrogram = dendrogram(row_links, no_plot=True)
        yind = row_dendrogram['leaves']
    else:
        yind = np.arange(0, data.shape[1])

    xmin,xmax = ax_col_dendrogram.get_xlim()
    im_heatmap = ax_heatmap.imshow(data.iloc[xind,yind].T, aspect='auto', extent=[xmin,xmax,0,1], cmap='YlOrRd', vmin=0, vmax=1, interpolation='none')
    ax_heatmap.set_yticks((data.columns.astype("int").to_series() - 0.5).div(data.shape[1]))
    ax_heatmap.set_yticklabels(data.columns[yind][::-1])
    ax_heatmap.set_ylabel("GEP", rotation=0, ha='right', va='center')
    ax_heatmap.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
    

    # Annotations
    if metadata is not None:
        # data and metadata must have the same index
        metadata = metadata.loc[data.index]
        missing_data_color = metadata_colors["missing_data"]
        gs2 = matplotlib.gridspec.GridSpecFromSubplotSpec(metadata.shape[1], 1, subplot_spec=gs0[2])
        for i, (track, annot) in enumerate(metadata.items()):
            ax = fig.add_subplot(gs2[i], sharex=ax_heatmap)
            ax.set_facecolor(missing_data_color)
            if pd.api.types.is_categorical_dtype(annot) or pd.api.types.is_object_dtype(annot):
                ordered_rgb = annot.iloc[xind].replace(metadata_colors[track])
                if ordered_rgb.isnull().any():
                    ordered_rgb = ordered_rgb.cat.add_categories(missing_data_color)
                    ordered_rgb = ordered_rgb.fillna(missing_data_color)
                ordered_rgb = ordered_rgb.astype("object").map(matplotlib.colors.to_rgb)
                ordered_rgb = np.array([list(rgb) for rgb in ordered_rgb])
                ax.imshow(np.stack([ordered_rgb, ordered_rgb]), aspect='auto', extent=[xmin,xmax,0,1], interpolation='none')
            else:
                ax.imshow(np.stack([annot.iloc[xind],annot.iloc[xind]]), aspect='auto', extent=[xmin,xmax,0,1], cmap='Blues', interpolation='none')
            ax.set_yticks([])
            ax.set_ylabel(track, rotation=0, ha='right', va='center')
            if ax.get_subplotspec().is_last_row():
                if show_sample_labels:
                    # print(ax.get_xticks())
                    # ax.set_xticks(np.linspace(0, 1, data.shape[0], endpoint=False) + 1/(2 * data.shape[0]))
                    ax.set_xticklabels(data.index[xind], rotation=90)
                else:
                    ax.set_xticks([])
            else:
                ax.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
    
    
    # Colormap for heatmap
    ax = fig.add_subplot(gs0[1])
    ax.set_axis_off()
    plt.colorbar(im_heatmap, ax=ax, location="top")
    
    # # old legend used to go here
    # # Category Legend
    # from matplotlib.patches import Patch
    # ax = fig.add_subplot(gs0[3])
    # # Add legend
    # legend_elements = []
    # for track, color_def in metadata_colors.items():
    #     if track in metadata.columns:
    #         legend_elements.append(Patch(label=track, facecolor='white', edgecolor=None, ))
    #         for cat, color in color_def.items():
    #             if cat in metadata[track].astype("category").cat.categories:
    #                 legend_elements.append(Patch(label=cat, facecolor=color, edgecolor=None))
    #         # if metadata[track].isnull().any():
    #         #     legend_elements.append(Patch(label="Other", facecolor=missing_data_color, edgecolor=None))

    # ax.legend(handles=legend_elements, loc='upper left')
    # ax.set_axis_off()
    return fig

def plot_annotated_usages(df, metadata, metadata_colors, title, filename, cluster_geps, cluster_samples, show_sample_labels):
    samples = df.index.to_series()
    df = df.div(df.sum(axis=1), axis=0)
    annotations = metadata.loc[samples]
    fig = annotated_heatmap(data=df, metadata=annotations, metadata_colors=metadata_colors, title=title, row_cluster=cluster_geps, col_cluster=cluster_samples, show_sample_labels=show_sample_labels)
    fig.savefig(filename, transparent=False, bbox_inches = "tight")
    plt.close(fig)  
    return fig

def plot_rank_reduction(df, max_median_corr_threshold):
    df = df.copy()    
    df["max_k"] = df.index
    fig, ax = plt.subplots(figsize=[df["max_k"].shape[0]/8, 6])
    ax.set_ylim([-1, 1])
    ax.set_xlim([df["max_k"].min() - 1, df["max_k"].max() + 1])
    ax.axhline(max_median_corr_threshold, color="red")
    ax.set_title("Median of the Correlation Distribution vs max_k")
    sns.lineplot(data=df, x="max_k", y="max_k_median_corr", hue="max_k_filter_pass", ax=ax, marker="o")
    plt.tight_layout()
    return fig

def plot_pairwise_corr(tril, thresholds=None):
    n_datasets = len(tril.index.levels[0])
    fig, axes = plt.subplots(n_datasets, n_datasets, figsize=[3 * n_datasets, 3 * n_datasets], sharex=True, sharey=True)
    for row, dataset_row in enumerate(tril.index.levels[0]):
        for col, dataset_col in enumerate(tril.columns.levels[0]):
            ax = axes[row,col]
            if row < col:
                ax.set_axis_off()
            else:
                corr = pd.Series(tril.loc[dataset_row, dataset_col].values.flatten()).dropna()
                if thresholds is not None:
                    min_corr = thresholds.loc[(dataset_row, dataset_col)].values[0]
                    hist_kwargs = {
                        "hue":[("Included" if c else "Excluded") for c in (corr > min_corr)],
                        "palette": {"Included": "red", "Excluded": "gray"},
                        "hue_order": ["Excluded", "Included"],
                        "linewidth": 0
                    }
                    included_fraction = (corr > min_corr).sum() / corr.shape[0]
                    ax.text(x=0.01, y=0.99, s=f"{included_fraction:.3f}", ha='left', va='top', transform=ax.transAxes, color="red", alpha=0.5)
                else:
                    hist_kwargs = {
                        "color": "gray",
                        "linewidth": 0
                    }
                sns.histplot(x=corr, ax=ax,legend=(row == 0)&(col == 0), **hist_kwargs)
                ax.set_ylabel(dataset_row)
                ax.set_xlabel(dataset_col)
                ax.set_xlim(-1,1)
    fig.suptitle(f"Correlation distribution between datasets")
    plt.tight_layout()
    return fig

def plot_pairwise_corr_overlaid(tril, thresholds):
    n_datasets = len(tril.index.levels[0])
    fig, axes = plt.subplots(n_datasets, n_datasets, figsize=[3 * n_datasets, 3 * n_datasets], sharex=True, sharey=True)
    for row, dataset_row in enumerate(tril.index.levels[0]):
        for col, dataset_col in enumerate(tril.columns.levels[0]):
            ax = axes[row,col]
            if row < col:
                ax.set_axis_off()
            else:
                corr = pd.DataFrame({"abscorr": tril.loc[dataset_row, dataset_col].values.flatten()}).dropna()
                corr["sign"] = (corr["abscorr"] >= 0).map({True: "Positive", False: "Negative"})
                corr["abscorr"] = corr["abscorr"].abs()
                sns.histplot(data=corr, x="abscorr", hue="sign", palette= {"Positive": "red", "Negative": "lightblue"}, alpha=0.5, linewidth=0,
                             hue_order= ["Negative", "Positive"], ax=ax,legend=(row == 0)&(col == 0))

                # show min_corr as text in top left of plot and vertical line
                min_corr = thresholds.loc[(dataset_row, dataset_col)].values[0]
                # included_fraction = (corr["abscorr"] > min_corr).sum() / corr.shape[0]  # could also show the quantile of the min_corr threshold
                ax.text(x=0.01, y=0.99, s=f"{min_corr:.3f}", ha='left', va='top', transform=ax.transAxes, color="black")
                ax.axvline(min_corr, color="black")
                
                ax.set_ylabel(dataset_row)
                ax.set_xlabel(dataset_col)
                ax.set_xlim(0,1)
    fig.suptitle(f"Correlation distribution between datasets")
    plt.tight_layout()
    return fig

def plot_genelist_upsets(config):
    overdispersed_genelists = {}
    full_genelists = {}
    for dataset_name, d in config.datasets.items():
        adata = read_h5ad(d["filename"])
        overdispersed_genelists[dataset_name] = list(adata.uns["gene_list"])
        full_genelists[dataset_name] = list(adata.var.index)
    figs = {}
    fig = plt.Figure()
    upsetplot.UpSet(upsetplot.from_contents(overdispersed_genelists)).plot(fig=fig)
    figs["overdispersed_genes.upset"] = fig
    fig = plt.Figure()
    upsetplot.UpSet(upsetplot.from_contents(full_genelists)).plot(fig=fig)
    figs["all_genes.upset"] = fig
    return figs

def plot_annotated_geps_by_community(usage, config, communities):
    figs = {}
    for dataset_name, dataset in config.datasets.items():
        metadata = read_h5ad(dataset["filename"], backed="r").obs.select_dtypes(include="category")  # only use categorical data
        # number of bars in each community for this dataset
        community_gep_counts = [len([node for node in communities[c] if node.split("|")[0] == dataset_name]) for c in sorted(list(communities))]
        width_ratios = [1 + gep_counts for gep_counts in community_gep_counts]
        fig, axes = plt.subplots(metadata.shape[1], len(communities), figsize=[2 + 0.1 * sum(community_gep_counts), metadata.shape[1] * 3], sharey='row', gridspec_kw={"width_ratios": community_gep_counts})
        for row, (annotation_layer, sample_to_class) in enumerate(metadata.items()):
            # usage subset to dataset
            ds_usage = usage.loc[:, (dataset_name, slice(None), slice(None))].dropna(how="all").droplevel(axis=0, level=0)
            ds_usage.index = ds_usage.index.map(sample_to_class)
            ds_usage = ds_usage[ds_usage.index.notnull()]
            observed = ds_usage.groupby(axis=0, level=0).sum()
            expected = []
            for k, obs_k in observed.groupby(axis=1, level=1):
                exp_k = pd.DataFrame(obs_k.sum(axis=1)) @ pd.DataFrame(obs_k.sum(axis=0)).T / obs_k.sum().sum()
                expected.append(exp_k)
            expected = pd.concat(expected, axis=1)
            chisq_resid = (observed - expected) / np.sqrt(expected)  # pearson residual of chi-squared test of contingency table
            overrepresentation = chisq_resid.clip(lower=0)
            for col, community in enumerate(sorted(list(communities))):
                ax = axes[row, col]
                geps = []
                for node in communities[community]:
                    dataset_str, k_str, gep_str = node.split("|")
                    if dataset_str == dataset_name:
                        geps.append((dataset_str, int(k_str), int(gep_str)))
                geps = sorted(geps)
                if geps:
                    overrepresentation[geps].T.plot.bar(stacked=True, width=0.9, ax=ax, legend=None, color=config.get_metadata_colors(annotation_layer))
                ax.set_xlabel("")
                ax.set_xticks([])
                if col == 0:
                    ax.set_ylabel(annotation_layer)
                if row == 0:
                    ax.set_title(community, size=14)

        fig.supxlabel("GEP")
        fig.supylabel("Overrepresentation")
        fig.suptitle("Community")
        figs[dataset_name] = fig
    return figs

def plot_community_by_dataset_rank(communities, config):
    """
    Plot communities by dataset and rank representation
    """

    marker_style = {
        1: ("s", 30),  # 1 factor: square markers, size 30
        2: (2, 30)     # 2 factors: marker #2 (up tick), size 30
        }
    dataset_colors = {ds: ds_attr["color"] for ds, ds_attr in config.datasets.items()}

    fig, axes = plt.subplots(1, len(config.datasets)+1, figsize=[1 + len(config.datasets)* 5,1 + len(communities)/4], sharex=True, sharey=True)
    for rownum, dataset in enumerate(config.datasets):
        for community, members in communities.items():
            counts = pd.Series([m.rpartition("|")[0] for m in members]).value_counts()
            
            # plot line if any factors are present
            line_x = []
            line_y = []
            for pos, rank in enumerate(config.datasets[dataset]["selected_k"]):
                line_x.append(pos)
                if f"{dataset}|{rank}" in counts.index:
                    line_y.append(community)
                else:
                    line_y.append(np.NaN)
            axes[rownum].plot(line_x, line_y, color=dataset_colors[dataset], linewidth=2)
            
            for count, style in marker_style.items():
                # plot different markers depending on how many factors are present:
                x = []
                y = []
                for pos, rank in enumerate(config.datasets[dataset]["selected_k"]):
                    factor_prefix = f"{dataset}|{rank}"
                    if factor_prefix in counts.index and counts[factor_prefix] == count:
                        x.append(pos)
                        y.append(community)
                axes[rownum].scatter(x, y, color=dataset_colors[dataset], marker=style[0], s=style[1])
        axes[rownum].set_yticks(list(communities.keys()))
        axes[rownum].set_xticks(list(range(len(config.datasets[dataset]["selected_k"]))))
        axes[rownum].set_xticklabels(config.datasets[dataset]["selected_k"])
        axes[rownum].set_title(dataset)

    fig.supxlabel("Rank (k)")
    fig.supylabel("Community")


    # Add legend
    cbdrlegend = []
    cbdrlegend.append(Line2D([0],[0], marker='s', color='black', label="1 GEP", markerfacecolor="black", markersize=8))
    cbdrlegend.append(Line2D([0],[0], marker=2, color='black', label="2 GEPs", markerfacecolor="black", markersize=8))
    cbdrlegend.append(Line2D([0],[0], marker=None, color='black', label="3+ GEPs", markerfacecolor="black", markersize=8))
    axes[-1].legend(handles=cbdrlegend, loc='center', frameon=False)
    axes[-1].set_axis_off()
    plt.tight_layout()
    return fig

            
def draw_circle_bar_plot(x, y, enrichments, colors, size, ax, draw_labels: bool=False, label_radius=0.2, label_font_size=1, draw_scale=False):
    ### TODO: implement draw_scale functionality
    if draw_scale:
        raise NotImplementedError
    previous = np.pi
    for color, (label, enrichment) in zip(colors, enrichments.items()):
        # calculate the points of the pie pieces
        this = previous - 2 * np.pi / len(enrichments)
        x_shape  = [0] + np.cos(np.linspace(previous, this, 40)).tolist() + [0]
        y_shape  = [0] + np.sin(np.linspace(previous, this, 40)).tolist() + [0]
        xy_shape = np.column_stack([x_shape, y_shape])
        # print(label, previous, this)
        # scatter each of the pie pieces
        marker = {'marker':xy_shape, 's':np.abs(xy_shape).max()**2*enrichment*size, 'facecolor':color, 'linewidths':0}
        ax.scatter([x], [y], **marker)
        # text
        if draw_labels:
            a = (previous - np.pi / len(enrichments))
            x_offset = label_radius * np.cos(a)
            y_offset = label_radius * np.sin(a)
            ax.text(x+x_offset, y+y_offset, label, rotation=np.rad2deg(a), ha="left", va="center", rotation_mode='anchor', fontsize=label_font_size)
        previous = this

def plot_overrepresentation_network(graph, layout, title, overrepresentation, colordict, plot_size, node_size, edge_weights=None):

    # Plot the network
    fig, ax = plt.subplots(figsize=plot_size)
    ax.set_axis_off()
    # nx.draw(G, pos=layout, with_labels=True, labels=labels, node_color="#AAAAAA", node_size=20, linewidths=0, width=0.2, font_size=2, edge_color="#888888", ax=ax)
    if edge_weights is None:
        width = 0.2
    else:
        width = np.array(list(nx.get_edge_attributes(graph, edge_weights).values()))
        width = width / np.max(width)

    nx.draw_networkx_edges(graph, pos=layout, edge_color="#888888", ax=ax, width=width)
    plotted_categories = set()
    for node, gep_or in overrepresentation.iteritems():
        if node in graph and gep_or.any():
            plotted_categories.update(gep_or.index)
            color_list = gep_or.index.map(colordict)
            x, y = layout[node]
            draw_circle_bar_plot(x, y, gep_or, colors=color_list, size=node_size * 10, ax=ax)

    # Add legend
    legend_bbox = [0.8,0.8,0.19, 0.19]
    ax.add_patch(FancyBboxPatch(legend_bbox[:2], legend_bbox[2], legend_bbox[3], fc='#ffffff88', ec="#aaaaaa", boxstyle="round,pad=0.01", transform=ax.transAxes))
    ax_legend = ax.inset_axes(legend_bbox)
    ax_legend.set_axis_off()
    ax_legend.set_ylim([0,1])
    ax_legend.set_xlim([0,1])
    draw_circle_bar_plot(
        0.5, 0.5,
        enrichments = pd.Series(1, index=gep_or.index.sort_values().unique()),
        colors=overrepresentation.index.map(colordict), size=node_size*16, draw_labels=True, label_font_size=6, ax=ax_legend)
    plt.tight_layout()
    return fig

def plot_overrepresentation_geps_bar(usage, metadata, communities, dataset_name, config):
    # usage subset to dataset
    ds_usage = usage.loc[:, (dataset_name, slice(None), slice(None))].dropna(how="all").droplevel(axis=0, level=0)
    # number of bars in each community for this dataset
    community_gep_counts = [len([node for node in communities[c] if node.split("|")[0] == dataset_name]) for c in sorted(list(communities))]
    fig, axes = plt.subplots(
        metadata.shape[1], len(communities),
        figsize=[len(communities) + 0.1 * sum(community_gep_counts), metadata.shape[1] * 3],
        sharey='row',
        gridspec_kw={"width_ratios": [gep_counts for gep_counts in community_gep_counts]})
    for row, (annotation_layer, sample_to_class) in enumerate(metadata.items()):
        overrepresentation = get_category_overrepresentation(ds_usage, sample_to_class)
        for col, community in enumerate(sorted(list(communities))):
            ax = axes[row, col]
            geps = []
            for node in communities[community]:
                dataset_str, k_str, gep_str = node.split("|")
                if dataset_str == dataset_name:
                    geps.append((dataset_str, int(k_str), int(gep_str)))
            geps = sorted(geps)
            if geps:
                overrepresentation[geps].T.plot.bar(stacked=True, width=0.9, ax=ax, legend=None, color=config.get_metadata_colors(annotation_layer))
            ax.set_xlabel("")
            ax.set_xticks([])
            if col == 0:
                ax.set_ylabel(annotation_layer)
            if row == 0:
                ax.set_title(community, size=14)

    fig.supxlabel("GEP")
    fig.supylabel("Overrepresentation")
    fig.suptitle("Community")
    return fig


def plot_number_of_patients(usage, sample_to_patient, G, layout, config):

    # normalized usage (usages sum to 1 for each value of k)
    normalized_usage = []
    for k, subdf in usage.groupby(axis=1, level=[0,1]):
        normalized_usage.append(subdf.div(subdf.sum(axis=1), axis=0))
    normalized_usage = pd.concat(normalized_usage, axis=1)
    normalized_usage

    # discrete usage (Samples are assigned to GEPs with the highest usage)
    discrete_usage = []
    for k, subdf in usage.groupby(axis=1, level=[0,1]):
        discrete_usage.append(subdf.eq(subdf.max(axis=1), axis=0).astype(float))
    discrete_usage = pd.concat(discrete_usage, axis=1)
    discrete_usage[usage.isnull()] = np.NaN

    patients_to_geps = discrete_usage.loc[sample_to_patient.keys()].copy(deep=True)
    patients_to_geps.index = patients_to_geps.index.map(sample_to_patient)
    patients_to_geps = patients_to_geps.groupby(axis=0, level=[0,1]).any()

    nodes = []
    for node in G.nodes:
        dataset_name, k_str, gep_str = node.split("|")
        nodes.append((dataset_name, int(k_str), int(gep_str)))

    dataset_colors = {ds: ds_attr["color"] for ds, ds_attr in config.datasets.items()}
    dataset_legend = []
    for dataset, color in dataset_colors.items():
        dataset_legend.append(Line2D([0], [0], marker='o', color='w', label=dataset, markerfacecolor=color, markersize=8))

    figs = {}
    for method in ('nsamples_continuous', 'nsamples_discrete', "npatients_discrete"):
        if method == 'nsamples_continuous':
            labels = normalized_usage[nodes].sum().apply(lambda x: "{:.1f}".format(x)).to_dict() # Label is number of samples
            sizes = (normalized_usage[nodes].sum() * 5).to_dict() # Size is proportional to number of samples
        elif method == 'nsamples_discrete':
            labels = discrete_usage[nodes].sum().apply(lambda x: int(x)).to_dict() # Label is number of samples
            sizes = (discrete_usage[nodes].sum() * 5).to_dict() # Size is proportional to number of samples
        elif method == "npatients_discrete":
            labels = patients_to_geps[nodes].sum().to_dict()
            sizes = (patients_to_geps.sum() * 5).to_dict()
        labels = {f"{k[0]}|{k[1]}|{k[2]}": v for k,v in labels.items()}
        sizes = {f"{k[0]}|{k[1]}|{k[2]}": v for k,v in sizes.items()}
        colors = [node.partition("|")[2] for node in G]
        node_sizes = [(sizes[n] if n in sizes else 0) for n in G]
        colors = [dataset_colors[node.split("|")[0]] for node in G]
        fig, ax = plt.subplots(figsize=config.sns["plot_size"])
        nx.draw(G, pos=layout,
        with_labels=True, labels=labels, node_color=colors, node_size=node_sizes, linewidths=0, width=0.2, edge_color=config.sns["edge_color"], font_size=3, ax=ax)
        ax.legend(handles=dataset_legend)
        ax.set_title(method)
        plt.tight_layout()
        figs[method] = fig
    return figs