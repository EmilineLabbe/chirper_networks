
"""
functions for sampling code

author: emi labbe
last update: july 5 2025
"""
import os
import pandas as pd
import numpy as np
import random
import networkx as nx
from collections import deque
import csv
import re


def find_users(data, href=None, user_name=None, user_id=None, show_actions=False):
    """
    returns all users associated with matching href or user_name(s)

    parameter href: 
    precondition: href is a str

    parameter user_name: 
    precondition: user_name is a str

    parameter user_id: 
    precondition: user_id is an int and a valid id in the data

    parameter show_actions: if True prints user action list(s)
    precondition: show_actions is a bool
    """

    if user_id is not None:
        users = data[data['id'] == user_id]
        #print("searching user_ids")
    elif href is not None:
        users = data[data['user_href'] == href]
        #print("searching user_hrefs")
    elif user_name is not None :
        users = data[data['user_name'].str.contains(user_name, na=False)]
        #print("searching user_names")

    if show_actions:
        for user, row in users.iterrows():
            print(f"{user}'s actions: {row['action_list']}")

    return users


def convert_follower_count(value):
    """
    returns an int, if value is a string
    test cases in functions_tests module

    parameter value:
    precondition: string
    """

    if isinstance(value, str):
        value = value.strip().upper().replace(',', '')
        if value.endswith('K'):
            return int(float(value[:-1]) * 1000)
        elif value.endswith('M'):
            return int(float(value[:-1]) * 1000000)
        elif value.endswith('FOLLOWS'):
            return int(float(value[:-8]))
        elif value.isdigit():
            return int(value)
        else:
            print(value)

    else:
        return value
    


def id_extractor(target_str, nodes_df):
    """
    returns id associated with target_str

    parameter target_str: user_name
    precondition: string
    """

    if not isinstance(target_str, str) or "Deleted" in target_str:
        return None
    if "'s chirp" not in target_str:
        return None

    username = target_str.split("'s chirp")[0].lstrip("@").strip().lower()
    match_row = nodes_df[nodes_df['user_name'].str.lower() == username]
    if not match_row.empty:
        return match_row.iloc[0]['id']
    

def name_to_id(nodes_df):
    """
    returns a dictionary with name keys mapped to id values
    """
    mapping = {}
    for name, uid in zip(nodes_df['user_name'], nodes_df['id']):
        if isinstance(name, str) and name.strip():
            clean_name = name.strip().lower().lstrip('@')
            mapping[clean_name] = uid
    return mapping


def extract_action_and_username(action_text):
    """
    returns action
    """
    if not isinstance(action_text, str):
        return None, None

    lowered = action_text.lower()

    #check for user_name
    for keyword, action_name in [(' liked ', 'like'), (' disliked ', 'dislike'), (' followed ', 'follow'), ('unfollowed ', 'unfollow')]:
        if keyword in lowered:
            part = action_text.split(keyword, 1)[1]
            if action_name in ['like', 'dislike'] and "'s chirp" in part:
                username = part.split("'s chirp", 1)[0].strip()
            else:
                username = part.strip()
            return action_name, username.lstrip('@')

    #check for action
    for prefix, action_name in [('liked ', 'like'), ('disliked ', 'dislike'), ('followed ', 'follow'), ('unfollowed ', 'unfollow')]:
        if lowered.startswith(prefix):
            part = action_text[len(prefix):]
            if action_name in ['like', 'dislike'] and "'s chirp" in part:
                username = part.split("'s chirp", 1)[0].strip()
            else:
                username = part.strip()
            return action_name, username.lstrip('@')



def remove_isolated_nodes(g):
    """
    return graph object g with isolated nodes removed
    """
    isolated = list(nx.isolates(g))
    g.remove_nodes_from(isolated)
    return g


#data saving

def export_subgraphs(graph, save_folder, edge_types=['like', 'dislike', 'follow', 'unfollow']):

    total_edges = 0

    for edge_type in edge_types:
        edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get('type') == edge_type]
        subgraph = graph.edge_subgraph(edges).copy()

        edge_filename = f"{edge_type}s_edges.csv"
        node_filename = f"{edge_type}s_nodes.csv"

        subgraph_to_csv(subgraph, edge_filename, node_filename, save_folder)
        print(f"\n{edge_type}s subgraph: {subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges")
        total_edges += subgraph.number_of_edges()

    #verify that nodes add up to total
    if total_edges == graph.number_of_edges():
        print("\nsubgraphs created successfully")
    else:
        print("\nsubgraph edges don't add up to total in original graph")

    return None

def subgraph_to_csv(graph, edge_filename, node_filename, save_folder):
    """
    helper function to create dataframes for edge and node data, then saves to csv with edge_filename and node_filename
    """
    edge_data = []
    for u, v, d in graph.edges(data=True):
        edge_row = {
            'source': graph.nodes[u].get('id', u),
            'target': graph.nodes[v].get('id', v),
            'source_user_href': graph.nodes[u].get('user_href', ''),
            'target_user_href': graph.nodes[v].get('user_href', ''),
            #'key': k,
            **d
        }
        edge_data.append(edge_row)

    pd.DataFrame(edge_data).to_csv(os.path.join(save_folder, edge_filename), index=False)

    node_data = [
        {
            'id': n,
            'user_name': graph.nodes[n].get('user_name'),
            'user_href': graph.nodes[n].get('user_href'),
            **{k: v for k, v in graph.nodes[n].items() if k not in ['user_name', 'user_href']}
        }
        for n in graph.nodes
    ]
    pd.DataFrame(node_data).drop_duplicates(subset='id').to_csv(os.path.join(save_folder, node_filename), index=False)

    return None


def match_edge_weight(graph, source, target, edge_type):

    edge_data = graph.get_edge_data(source, target)

    if edge_data is None:
        return None

    if isinstance(edge_data, dict) and any(isinstance(edge, int) for edge in edge_data.keys()):
        for edge, attrs in edge_data.items():
            if isinstance(attrs, dict) and attrs.get('type') == edge_type:
                return attrs.get('weight', 1)
        return None
    
    elif isinstance(edge_data, dict) and edge_data.get('type') == edge_type:
        return edge_data.get('weight', 1)
    
    return None


def check_weighted_graph_validity(sampled_g, original_g):
    """
    verifies that nodes and edges were not duplicated during sampling
    """
    missing_nodes = set(sampled_g.nodes()) - set(original_g.nodes())
    if missing_nodes:
        print(f"nodes in sampled graph missing from original: {missing_nodes}")
    else:
        print("all sampled nodes valid")

    errors_found = False
    for u, v, data in sampled_g.edges(data=True):
        sampled_weight = data.get('weight', 1)
        sampled_type = data.get('type')

        if original_g.has_edge(u, v):
            orig_data = original_g.get_edge_data(u, v)
            
            if isinstance(orig_data, dict) and all(isinstance(k, int) for k in orig_data.keys()):
                #check all parallel edges for matching type
                matched = False
                for key, attr in orig_data.items():
                    if attr.get('type') == sampled_type:
                        orig_weight = attr.get('weight', 1)
                        if orig_weight < sampled_weight:
                            print(f"edge {u} to {v} (type '{sampled_type}') has weight {sampled_weight} in sample, {orig_weight} in original")
                            errors_found = True
                        matched = True
                        break
                if not matched:
                    print(f"edge {u} to {v} (type '{sampled_type}') is missing in original graph")
                    errors_found = True
            else:
                #edge case
                if orig_data.get('type') == sampled_type:
                    orig_weight = orig_data.get('weight', 1)
                    if orig_weight < sampled_weight:
                        print(f"edge {u} to {v} (type '{sampled_type}') has weight {sampled_weight} in sample, {orig_weight} in original")
                        errors_found = True
                else:
                    print(f"edge {u} to {v} (type '{sampled_type}') is missing in original graph")
                    errors_found = True
        else:
            print(f"edge {u} to {v} is missing in original graph")
            errors_found = True

    if not errors_found:
        print("all edges in sampled graph are valid")

    return None