"""
functions for analysis code

author: emi labbe
last update: july 4 2025
"""

import os
import sys
import warnings
import contextlib
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors
import powerlaw


#mapping paths to interaction types
interaction_paths = {
    'All':      'sampled_chirper_networks/sample_edges.csv',
    'Follows':  'sampled_chirper_networks/follows_edges.csv',
    'Unfollows':'sampled_chirper_networks/unfollows_edges.csv',
    'Likes':    'sampled_chirper_networks/likes_edges.csv',
    'Dislikes': 'sampled_chirper_networks/dislikes_edges.csv',
}


##loading
def load_graph_from_csv(path, source_col='Source', target_col='Target'):
    """
    load directed graph from path. helper function for plot_powerlaw

    """

    #read CSV
    df = pd.read_csv(path)
    #build digraph
    G = nx.from_pandas_edgelist(
        df,
        source=source_col,
        target=target_col,
        create_using=nx.DiGraph()
    )
    return G


def load_interaction_graphs(paths_dict=interaction_paths):
    """
    load directed nx graphs interaction_paths

    """
    graphs = {}
    for label, path in paths_dict.items():
        df = pd.read_csv(path)
        G = nx.from_pandas_edgelist(df, source='source', target='target', create_using=nx.DiGraph())
        graphs[label.title()] = G.to_directed()

    return graphs


##computing
def compute_degrees(graphs):
    """
    returns total, in, and out degree lists for each graph

    """
    degree_data = defaultdict(dict)

    for label, i in graphs.items():
        degree_data[label]['Total'] = [d for node, d in i.degree() if d > 0]
        degree_data[label]['In']    = [d for node, d in i.in_degree() if d > 0]
        degree_data[label]['Out']   = [d for node, d in i.out_degree() if d > 0]

    return degree_data


def reciprocity_stats(graph):
    """ 
    returns action type reciprocity stats for graph G

    """
    mutual = 0
    one_sided = 0

    for u, v in graph.edges():
        if graph.has_edge(v, u):
            mutual+=1
        else:
            one_sided+=1
    
    mutual_connections = mutual//2 #divide by 2 to get actual mutual connections
    total_edges = graph.number_of_edges()

    stats = {
        'total_edges': total_edges,
        'mutual_edges': mutual_connections,
        'one_sided_edges': one_sided,
        'mutual_ratio': mutual_connections/total_edges if total_edges > 0 else 0
    }

    return stats


def fit_powerlaw(seq, plot=False):
    """
    returns powerlaw stats. fits a discrete power law, print α, xmin, and compare to lognormal

    """
    if plot:
        with open(os.devnull, 'w') as devnull: 
            with contextlib.redirect_stdout(devnull):
                fit = powerlaw.Fit(seq, discrete=True)
    else:
        fit = powerlaw.Fit(seq, discrete=True)

    α = fit.power_law.alpha
    xmin = fit.power_law.xmin
    R, p = fit.distribution_compare('power_law', 'lognormal')

    # print(f"{label} : α = {α:.4f}, xmin = {xmin},  power_law vs lognormal: R={R:.4f}, p={p:.4f}")
    # print("-"*50)

    calculated = f"<br>α = {α:.4f}, xmin = {xmin}<br>power_law vs lognormal: R={R:.4f}, p={p:.4f}"

    return calculated



##plotting
def plot_degree_distribution(seq, title):
    """
    returns plotly fig of scatter plot of degree counts on log–log axes. helper function 
    for plot_powerlaw

    """
    counts = Counter(seq)
    degrees, freqs = zip(*sorted(counts.items()))

    fig = go.Figure(data=go.Scatter(
        x=degrees,
        y=freqs,
        mode='markers',
        marker=dict(size=6, color='blue')
    ))
    
    fig.update_layout(
        title=f"{title} Degree Dist. (log–log)",
        xaxis=dict(title='Degree', type='log', dtick=1),
        yaxis=dict(title='Frequency', type='log', dtick=1),
        template='plotly_white'
    )

    return fig


def plot_powerlaw(action_type):
    """
    plots 1 row 3 plotly subplots of powerlaw on log–log axes

    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        csv_path = os.path.join('outputs',f'{action_type}_edges.csv')
        src_col  = "source"            
        tgt_col  = "target"                    

        graph = load_graph_from_csv(csv_path, src_col, tgt_col) #load

        if not graph.is_directed(): #make directed if not already
            graph = graph.to_directed()

        #get degree seq
        total_deg = [d for node, d in graph.degree() if d >0]
        in_deg    = [d for node, d in graph.in_degree() if d >0]
        out_deg   = [d for node, d in graph.out_degree() if d >0]

        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=["Total Degree", "In Degree", "Out Degree"]
        )

        fig_total = plot_degree_distribution(total_deg, "Total")
        fig_in = plot_degree_distribution(in_deg, "In")
        fig_out = plot_degree_distribution(out_deg, "Out")

        total_powerlaw = fit_powerlaw(total_deg, plot=True)
        in_powerlaw = fit_powerlaw(in_deg,  plot=True)
        out_powerlaw = fit_powerlaw(out_deg, plot=True)

        powerlaw_map = [total_powerlaw, in_powerlaw, out_powerlaw]

        for i, subfig in enumerate([fig_total, fig_in, fig_out], start=1):
                
            for trace in subfig.data:
                fig.add_trace(trace, row=1, col=i)

            fig.update_xaxes(title_text=f"Degree <br><sup>{powerlaw_map[i-1]}</sup>", 
                            type='log', 
                            row=1, 
                            col=i, 
                            dtick=1)
                
            fig.update_yaxes(title_text="Frequency", 
                            type='log', 
                            row=1, 
                            col=i, 
                            dtick=1)

        fig.update_layout(
        title_text=f"{action_type.title()} Degree Distributions (log–log)",
        template='plotly_white',
        height=400,
        width=1000,
        showlegend=False
    )
        #plot
        fig.show()
        return fig


def plot_comparative_degree_plotly(degree_data):
    """
    plots 1 row 3 plotly subplots of powerlaw for all interaction types on log–log axes

    """
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["Total Degree", "In Degree", "Out Degree"]
    )

    degree_types = ['Total', 'In', 'Out']

    labels = list(degree_data.keys()) #distinct color for each label/interaction type
    palette = plotly.colors.qualitative.Plotly
    colors = {label: palette[i] for i, label in enumerate(labels)}

    for col, degree_type in enumerate(degree_types, start=1):
        for label, degs in degree_data.items():
            seq = degs.get(degree_type, [])
            if not seq:
                continue
            
            counts = Counter(seq)
            degrees, freqs = zip(*sorted(counts.items()))
            filtered = [(d, f) for d, f in zip(degrees, freqs) if d > 0 and f > 0]
            if not filtered:
                continue

            degrees, freqs = zip(*filtered)
            fig.add_trace(go.Scatter(
                x=degrees,
                y=freqs,
                mode='markers',
                name=label,
                showlegend=(col == 1),
                marker=dict(size=6, color=colors[label]),
                opacity=0.7
            ),
            row=1, col=col
            )

        fig.update_xaxes(title_text="Degree", type='log', dtick=1, row=1, col=col)
        fig.update_yaxes(title_text="Frequency", type='log', dtick=1, row=1, col=col)

    fig.update_layout(
        title_text="Degree Distributions (log–log) Across Interaction Types",
        template='plotly_white',
        height=400,
        width=1100,
        showlegend=True
    )
    fig.show()
    return fig


def plot_interaction_feature_correlation(interaction_paths=interaction_paths):
    """ 
    plots correlation matrix for interaction types in interaction path excluding "All"

    """
    graphs = load_interaction_graphs(interaction_paths)

    all_nodes = set() #get all unique node instances
    for G in graphs.values():
        all_nodes.update(G.nodes())

    #degree feature matrix
    feature_dict = defaultdict(dict)
    for label, G in graphs.items():
        out_deg_dict = dict(G.out_degree())
        for node in all_nodes:
            feature_dict[node][label] = out_deg_dict.get(node, 0)

    df_features = pd.DataFrame.from_dict(feature_dict, orient='index').fillna(0)

    #compute correlation
    selected = ['Follows', 'Unfollows', 'Likes', 'Dislikes']
    corr = df_features[selected].corr()

    #plot
    fig = go.Figure(
        data=[go.Heatmap(
            z=corr,
            x=corr.columns,
            y=corr.columns,
            colorscale=px.colors.diverging.RdBu[::-1],  #reverse colorscale
            zmin=0,
            zmax=1
        )]
    )

    fig.update_layout(
        title=dict(
            text="Correlation Matrix of Interaction Features",
            x=0.5),
        xaxis=dict(scaleanchor="y", constrain="domain", tickfont=dict(size=12), automargin=True),
        yaxis=dict(scaleanchor="x", constrain="domain", tickfont=dict(size=12), automargin=True)
    )

    fig.show()
    return fig
